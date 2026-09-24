import json
import logging
import queue
import threading
from typing import Generator
from flask import Blueprint, jsonify, request, Response
import pandas as pd


from api_routes.state import (
    SYNCED_CACHE_PATH,
    TOKEN_FILE_PATH,
    get_auth_token_from_request,
    get_classifier,
    set_dataset_cache,
)
import yandex_api

logger = logging.getLogger(__name__)

auth_sync_bp = Blueprint("auth_sync", __name__)


@auth_sync_bp.route("/api/auth/device-code", methods=["POST"])
def auth_device_code():
    data, err = yandex_api.request_yandex_device_code()
    if err or not data:
        return jsonify({"success": False, "error": err or "Не удалось получить код устройства"}), 400
    return jsonify({"success": True, **data})


@auth_sync_bp.route("/api/auth/poll-token", methods=["POST"])
def auth_poll_token():
    payload = request.get_json(silent=True) or {}
    device_code = payload.get("device_code", "").strip()
    if not device_code:
        return jsonify({"success": False, "error": "Не передан device_code"}), 400

    token, err = yandex_api.poll_yandex_device_token(device_code)
    if not token:
        return jsonify({"success": False, "status": "pending", "message": err or "Ожидание подтверждения"}), 200

    client, user_info, login_err = yandex_api.login_yandex(token)
    if login_err or not client:
        return jsonify({"success": False, "error": login_err or "Ошибка валидации полученного токена"}), 400

    try:
        with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(token)
    except OSError as e:
        logger.debug("Could not write token file: %s", e)

    return jsonify({"success": True, "token": token, "user": user_info})


def _process_and_save_likes(likes_df: pd.DataFrame, token: str) -> None:
    classifier = get_classifier()
    genres = [
        classifier.classify_track(a, t, aa, allow_network=False)[0]
        for a, t, aa in zip(likes_df["artist_raw"], likes_df["title_raw"], likes_df["all_artists"])
    ]
    likes_df["genre_cluster"] = genres
    likes_df["artists_count"] = likes_df["all_artists"].apply(lambda a: len(a) if isinstance(a, list) else 1)
    likes_df["is_collab"] = likes_df["artists_count"] > 1

    set_dataset_cache(likes_df)
    try:
        likes_df.to_pickle(SYNCED_CACHE_PATH)
        with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(token)
    except (IOError, OSError, ValueError) as ex:
        logger.warning("Не удалось сохранить кэш синхронизации: %s", ex)


@auth_sync_bp.route("/api/sync-likes", methods=["POST"])
def sync_likes():
    token = get_auth_token_from_request()
    if not token:
        return jsonify({"success": False, "error": "Требуется токен авторизации (token)"}), 400

    client, user_info, err = yandex_api.login_yandex(token)
    if err or not client:
        return jsonify({"success": False, "error": err or "Ошибка авторизации по токену"}), 401

    likes_df = yandex_api.fetch_user_likes_df(client)
    if likes_df is None or likes_df.empty:
        return jsonify({"success": False, "error": "Не удалось загрузить треки или коллекция пуста"}), 400

    _process_and_save_likes(likes_df, token)
    return jsonify({
        "success": True,
        "tracks_synced": len(likes_df),
        "user": user_info,
        "message": f"Успешно синхронизировано {len(likes_df):,} треков!",
    })


def _run_sync_worker(token: str, q: queue.Queue) -> None:
    try:
        q.put({"type": "progress", "stage": "auth", "percent": 2, "message": "Подключение к Яндекс Музыке..."})
        client, user_info, err = yandex_api.login_yandex(token)
        if err or not client:
            q.put({"type": "error", "stage": "error", "percent": 0, "message": err or "Недействительный токен"})
            return

        title = user_info.get("full_name") or user_info.get("login") or "Пользователь"
        q.put({"type": "progress", "stage": "fetching_init", "percent": 5, "message": f"Авторизован: {title}..."})

        def on_prog(cur: int, tot: int, msg: str):
            scaled = int(5 + (cur * 0.80))
            q.put({"type": "progress", "stage": "fetching", "percent": min(85, max(5, scaled)), "current": cur, "total": tot, "message": msg})

        likes_df = yandex_api.fetch_user_likes_df(client, progress_callback=on_prog)
        if likes_df is None or likes_df.empty:
            q.put({"type": "error", "stage": "error", "percent": 0, "message": "Медиатека пуста или ошибка загрузки"})
            return

        total_tracks = len(likes_df)
        q.put({"type": "progress", "stage": "classifying", "percent": 88, "message": f"Классификация {total_tracks:,} треков..."})
        _process_and_save_likes(likes_df, token)

        q.put({"type": "complete", "stage": "done", "percent": 100, "current": total_tracks, "total": total_tracks, "message": f"Синхронизировано {total_tracks:,} треков!"})
    except Exception as e:
        q.put({"type": "error", "stage": "error", "percent": 0, "message": f"Ошибка: {e}"})
    finally:
        q.put(None)


def stream_queue_events(q: queue.Queue, timeout: int = 20) -> Generator[str, None, None]:
    while True:
        try:
            item = q.get(timeout=timeout)
            if item is None:
                break
            ev_name = item.get("type", "message")
            yield f"event: {ev_name}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
        except queue.Empty:
            yield ": keepalive\n\n"


@auth_sync_bp.route("/api/sync-likes/stream", methods=["GET", "POST"])
def sync_likes_stream():
    token = get_auth_token_from_request()
    if not token:
        return jsonify({"success": False, "error": "Токен авторизации (token) не указан"}), 400

    q: queue.Queue = queue.Queue()
    threading.Thread(target=_run_sync_worker, args=(token, q), daemon=True).start()

    return Response(
        stream_queue_events(q, timeout=20),
        mimetype="text/event-stream",
        headers={
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
