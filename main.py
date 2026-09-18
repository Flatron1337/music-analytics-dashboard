import asyncio
import os
import signal
import subprocess
import sys
from typing import Optional, Set
import aiohttp
from aiohttp import web

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

streamlit_process: Optional[subprocess.Popen] = None
flask_process: Optional[subprocess.Popen] = None


def start_subprocesses() -> None:
    global streamlit_process, flask_process

    python_executable = sys.executable

    print(f"[*] Запуск Streamlit (Веб-версия) на порту {STREAMLIT_PORT}...")
    streamlit_cmd = [
        python_executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        f"--server.port={STREAMLIT_PORT}",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]
    streamlit_process = subprocess.Popen(streamlit_cmd)

    print(f"[*] Запуск REST API (Мобильный бэкенд) на порту {FLASK_API_PORT}...")
    flask_env = os.environ.copy()
    flask_env["PORT"] = str(FLASK_API_PORT)
    flask_cmd = [python_executable, "-u", "api.py"]
    flask_process = subprocess.Popen(flask_cmd, env=flask_env)


def stop_subprocesses() -> None:
    global streamlit_process, flask_process
    print("\n[*] Завершение внутренних процессов...")

    if streamlit_process:
        try:
            streamlit_process.terminate()
            streamlit_process.wait(timeout=3)
        except Exception:
            streamlit_process.kill()
        print("[+] Процесс Streamlit остановлен.")

    if flask_process:
        try:
            flask_process.terminate()
            flask_process.wait(timeout=3)
        except Exception:
            flask_process.kill()
        print("[+] Процесс REST API остановлен.")


async def proxy_websocket(request: web.Request, target_ws_url: str) -> web.WebSocketResponse:
    raw_proto = request.headers.get("Sec-WebSocket-Protocol", "")
    protocols = [p.strip() for p in raw_proto.split(",") if p.strip()]

    ws_client = web.WebSocketResponse(
        protocols=tuple(protocols) if protocols else None,
        autoclose=True,
        autoping=True,
    )
    await ws_client.prepare(request)

    client_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS
        and not k.lower().startswith("sec-websocket-")
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(
                target_ws_url,
                headers=client_headers,
                protocols=tuple(protocols) if protocols else None,
                autoclose=True,
                autoping=True,
            ) as ws_server:

                async def client_to_server():
                    async for msg in ws_client:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_server.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_server.send_bytes(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
                            break

                async def server_to_client():
                    async for msg in ws_server:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_client.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_client.send_bytes(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING):
                            break

                await asyncio.gather(
                    client_to_server(),
                    server_to_client(),
                    return_exceptions=True,
                )
        except Exception as e:
            print(f"[!] Ошибка WebSocket-прокси: {e}")
        finally:
            if not ws_client.closed:
                await ws_client.close()

    return ws_client


async def proxy_http_request(request: web.Request, target_base_url: str) -> web.Response:
    url_suffix = request.path_qs
    target_url = f"{target_base_url}{url_suffix}"

    body = await request.read()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != "host"
    }

    max_retries = 4
    retry_delay = 1.2

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body,
                    allow_redirects=False,
                    timeout=aiohttp.ClientTimeout(total=45),
                ) as upstream_response:
                    content = await upstream_response.read()

                    response_headers = {}
                    for k, v in upstream_response.headers.items():
                        if k.lower() not in HOP_BY_HOP_HEADERS:
                            response_headers[k] = v

                    return web.Response(
                        body=content,
                        status=upstream_response.status,
                        headers=response_headers,
                    )
        except aiohttp.ClientConnectorError:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                continue
            return web.Response(
                text="Бэкенд сервис прогревается, повторите запрос через пару секунд...",
                status=503,
                content_type="text/plain",
                charset="utf-8",
            )
        except Exception as e:
            return web.Response(
                text=f"Ошибка проксирования: {e}",
                status=502,
                content_type="text/plain",
                charset="utf-8",
            )

    return web.Response(
        text="Служба временно недоступна",
        status=503,
        content_type="text/plain",
        charset="utf-8",
    )


async def router_handler(request: web.Request) -> web.StreamResponse:
    # 1. WebSocket proxy for Streamlit
    if request.headers.get("Upgrade", "").lower() == "websocket":
        target_ws = f"ws://127.0.0.1:{STREAMLIT_PORT}{request.path_qs}"
        return await proxy_websocket(request, target_ws)

    # 2. REST API requests (starting with /api/) -> Flask API
    if request.path.startswith("/api/"):
        return await proxy_http_request(request, f"http://127.0.0.1:{FLASK_API_PORT}")

    # 3. All other requests (Web UI) -> Streamlit
    return await proxy_http_request(request, f"http://127.0.0.1:{STREAMLIT_PORT}")


def init_app() -> web.Application:
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", router_handler)
    return app


def main():
    start_subprocesses()

    port = int(os.environ.get("PORT", 10000))
    print("=" * 65)
    print(" 🚀 MUSIC ANALYTICS UNIFIED ROUTER (WEB + MOBILE)")
    print("=" * 65)
    print(f" 🌐 Внешний порт:       http://0.0.0.0:{port}")
    print(" 💻 Веб-сайт (Streamlit): http://localhost:8501 (по корню '/')")
    print(" 📱 Mobile API (Flask):   http://localhost:5001 (по пути '/api/')")
    print("=" * 65)

    app = init_app()

    def handle_signal(sig, frame):
        stop_subprocesses()
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
    except Exception:
        pass

    try:
        web.run_app(app, host="0.0.0.0", port=port, print=None)
    finally:
        stop_subprocesses()


if __name__ == "__main__":
    main()
