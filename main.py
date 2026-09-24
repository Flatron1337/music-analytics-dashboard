import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Dict, Optional, Set
import aiohttp
from aiohttp import web

logger = logging.getLogger(__name__)

STREAMLIT_PORT = 8501
FLASK_API_PORT = 5001

HOP_BY_HOP_HEADERS: Set[str] = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}

STATIC_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".svg", ".ico", ".css", ".js", ".woff", ".woff2", ".ttf"
)

APK_PATH = os.path.join(os.path.dirname(__file__), "yndex_mobile", "app-release.apk")

streamlit_process: Optional[subprocess.Popen] = None
flask_process: Optional[subprocess.Popen] = None


def start_subprocesses() -> None:
    global streamlit_process, flask_process
    py_exec = sys.executable

    print(f"[*] [1/2] Запуск REST API (Мобильный бэкенд) на порту {FLASK_API_PORT}...", flush=True)
    flask_env = os.environ.copy()
    flask_env["PORT"] = str(FLASK_API_PORT)
    flask_env["FLASK_HOST"] = "127.0.0.1"
    flask_process = subprocess.Popen([py_exec, "-u", "api.py"], env=flask_env)

    time.sleep(1.2)

    print(f"[*] [2/2] Запуск Streamlit (Веб-интерфейс) на порту {STREAMLIT_PORT}...", flush=True)
    streamlit_cmd = [
        py_exec, "-m", "streamlit", "run", "app.py",
        f"--server.port={STREAMLIT_PORT}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    streamlit_process = subprocess.Popen(streamlit_cmd)


def stop_subprocesses() -> None:
    global streamlit_process, flask_process
    print("\n[*] Завершение внутренних процессов...", flush=True)

    for proc, name in [(streamlit_process, "Streamlit"), (flask_process, "REST API")]:
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
            print(f"[+] Процесс {name} остановлен.", flush=True)


async def proxy_websocket(request: web.Request, target_ws_url: str) -> web.WebSocketResponse:
    raw_proto = request.headers.get("Sec-WebSocket-Protocol", "")
    protocols = [p.strip() for p in raw_proto.split(",") if p.strip()]

    ws_client = web.WebSocketResponse(protocols=tuple(protocols) if protocols else None, autoclose=True, autoping=True)
    await ws_client.prepare(request)

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and not k.lower().startswith("sec-websocket-")
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(
                target_ws_url, headers=headers, protocols=tuple(protocols) if protocols else None, autoclose=True, autoping=True
            ) as ws_server:
                async def c2s():
                    async for msg in ws_client:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_server.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_server.send_bytes(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
                            break

                async def s2c():
                    async for msg in ws_server:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_client.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_client.send_bytes(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
                            break

                await asyncio.gather(c2s(), s2c(), return_exceptions=True)
        except Exception as e:
            logger.warning("Ошибка WebSocket-прокси: %s", e)
        finally:
            if not ws_client.closed:
                await ws_client.close()

    return ws_client


def _filter_client_headers(request: web.Request) -> Dict[str, str]:
    return {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != "host"
    }


async def _handle_stream_proxy(upstream_resp: aiohttp.ClientResponse, req: web.Request, headers: dict) -> web.StreamResponse:
    stream_resp = web.StreamResponse(status=upstream_resp.status, headers=headers)
    await stream_resp.prepare(req)
    async for chunk in upstream_resp.content.iter_any():
        await stream_resp.write(chunk)
    await stream_resp.write_eof()
    return stream_resp


async def proxy_http_request(request: web.Request, target_base_url: str) -> web.StreamResponse:
    target_url = f"{target_base_url}{request.path_qs}"
    body = await request.read()
    req_data = body if (request.method not in ("GET", "HEAD") and len(body) > 0) else None
    headers = _filter_client_headers(request)

    accept_hdr = request.headers.get("Accept", "").lower()
    is_stream = "event-stream" in accept_hdr or "stream" in request.path.lower()
    timeout = aiohttp.ClientTimeout(total=300 if is_stream else 45, connect=12)

    for attempt in range(4):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=request.method, url=target_url, headers=headers, data=req_data, allow_redirects=False
                ) as up_resp:
                    content_type = up_resp.headers.get("Content-Type", "").lower()
                    resp_headers = {k: v for k, v in up_resp.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}

                    if any(request.path.lower().endswith(ext) for ext in STATIC_EXTENSIONS):
                        resp_headers.setdefault("Cache-Control", "public, max-age=86400, stale-while-revalidate=604800")

                    if "text/event-stream" in content_type or is_stream:
                        return await _handle_stream_proxy(up_resp, request, resp_headers)

                    content = await up_resp.read()
                    resp = web.Response(body=content, status=up_resp.status, headers=resp_headers)
                    resp.enable_compression()
                    return resp
        except aiohttp.ClientConnectorError:
            if attempt < 3:
                await asyncio.sleep(1.2)
                continue
            return web.Response(text="Сервис инициализируется, повторите запрос...", status=503, content_type="text/plain; charset=utf-8")
        except Exception as e:
            logger.warning("Proxy error for %s: %s", target_url, e)
            return web.Response(text=f"Ошибка проксирования: {e}", status=502, content_type="text/plain; charset=utf-8")

    return web.Response(text="Служба временно недоступна", status=503, content_type="text/plain; charset=utf-8")


async def download_apk_handler(_: web.Request) -> web.StreamResponse:
    """Прямая отдача собранного Android APK приложения для скачивания со смартфона."""
    if not os.path.exists(APK_PATH):
        return web.Response(text="APK файл ещё не собран на сервере", status=404, content_type="text/plain; charset=utf-8")
    return web.FileResponse(
        APK_PATH,
        headers={
            "Content-Type": "application/vnd.android.package-archive",
            "Content-Disposition": 'attachment; filename="app-release.apk"',
            "Cache-Control": "public, max-age=3600",
        },
    )


async def router_handler(request: web.Request) -> web.StreamResponse:
    if request.path in ("/download/apk", "/download/app-release.apk"):
        return await download_apk_handler(request)

    if request.headers.get("Upgrade", "").lower() == "websocket":
        target_ws = f"ws://127.0.0.1:{STREAMLIT_PORT}{request.path_qs}"
        return await proxy_websocket(request, target_ws)

    if request.path.startswith("/api/"):
        return await proxy_http_request(request, f"http://127.0.0.1:{FLASK_API_PORT}")

    return await proxy_http_request(request, f"http://127.0.0.1:{STREAMLIT_PORT}")


def init_app() -> web.Application:
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", router_handler)
    return app


def main() -> None:
    start_subprocesses()
    port = int(os.environ.get("PORT", 10000))

    print("=" * 65, flush=True)
    print(" 🚀 MUSIC ANALYTICS UNIFIED ROUTER (WEB + MOBILE)", flush=True)
    print(f" 🌐 Внешний порт:         http://0.0.0.0:{port}", flush=True)
    print(f" 📱 Скачивание APK:       http://0.0.0.0:{port}/download/apk", flush=True)
    print("=" * 65, flush=True)

    app = init_app()

    def handle_signal(_sig, _frame):
        stop_subprocesses()
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    except (ValueError, AttributeError, OSError) as e:
        logger.debug("Signal handler registration skipped: %s", e)

    try:
        web.run_app(app, host="0.0.0.0", port=port)
    finally:
        stop_subprocesses()


if __name__ == "__main__":
    main()
