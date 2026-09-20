import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse

import pandas as pd
from yandex_music import Client
from yandex_music.exceptions import UnauthorizedError, YandexMusicError
from yandex_music.utils.difference import Difference

from parser import extract_artists


def extract_token_from_string(raw: str) -> Optional[str]:
    """Извлекает OAuth-токен Яндекс ID из строки или полного URL редиректа."""
    if not raw:
        return None
    s = raw.strip().strip("'\"")

    # Если передан сразу токен вида y0_...
    if s.startswith("y0_"):
        return s

    # Если передан URL с параметром access_token в query или hash (#access_token=y0_...)
    match = re.search(r"access_token=([a-zA-Z0-9_\-\.]+)", s)
    if match:
        return match.group(1)

    # Если передана строка длиннее 15 символов без пробелов
    if len(s) > 15 and " " not in s and "/" not in s and "?" not in s and "&" not in s:
        return s

    return None


def request_yandex_device_code() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Запрашивает одноразовый код для официальной авторизации через ya.ru/device (Device Flow)."""
    try:
        client = Client()
        dc = client.request_device_code()
        return {
            "device_code": dc.device_code,
            "user_code": dc.user_code,
            "verification_url": dc.verification_url or "https://ya.ru/device",
            "expires_in": dc.expires_in,
            "interval": dc.interval,
        }, None
    except Exception as err:
        return None, f"Не удалось получить код авторизации: {err}"


def poll_yandex_device_token(device_code: str) -> Tuple[Optional[str], Optional[str]]:
    """Проверяет подтверждение входа пользователем на ya.ru/device."""
    try:
        client = Client()
        oauth_token = client.poll_device_token(device_code)
        if oauth_token and oauth_token.access_token:
            return oauth_token.access_token, None
        return None, "Вход ещё не подтверждён на странице ya.ru/device. Введите код и нажмите «Проверить вход»."
    except Exception as err:
        err_msg = str(err)
        if "authorization_pending" in err_msg:
            return None, "Вход ещё не подтверждён на странице ya.ru/device. Введите код и нажмите «Проверить вход»."
        return None, f"Ошибка при проверке кода: {err}"


def login_yandex(
    token: str,
) -> Tuple[Optional[Client], Optional[Dict[str, Any]], Optional[str]]:
    """Инициализирует и проверяет сессию клиента Яндекс Музыки.

    Возвращает (client, account_info, error_message).
    """
    cleaned_token = extract_token_from_string(token)
    if not cleaned_token:
        return None, None, "Некорректный формат токена. Токен должен начинаться с 'y0_' или быть URL перенаправления."

    try:
        client = Client(cleaned_token).init()
        account = client.me.account
        user_info = {
            "uid": account.uid,
            "login": account.login or str(account.uid),
            "full_name": account.full_name or account.login or "Пользователь",
            "second_name": account.second_name or "",
            "avatar_url": f"https://avatars.yandex.net/get-yapic/{account.default_avatar_id}/islands-200"
            if getattr(account, "default_avatar_id", None)
            else None,
        }
        return client, user_info, None
    except UnauthorizedError:
        return None, None, "Ошибка авторизации: токен недействителен или срок его действия истёк."
    except Exception as err:
        return None, None, f"Ошибка подключения к Яндекс Музыке: {err}"


def fetch_user_likes_df(
    client: Client,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    batch_size: int = 500,
) -> pd.DataFrame:
    """Загружает всю коллекцию 'Мне нравится' пользователя и преобразует в структурированный DataFrame."""
    if progress_callback:
        progress_callback(0, 100, "Получение списка идентификаторов треков...")

    likes_obj = client.users_likes_tracks()
    if not likes_obj or not likes_obj.tracks:
        return pd.DataFrame()

    tracks_short = likes_obj.tracks
    total_tracks = len(tracks_short)
    track_ids = [t.id for t in tracks_short]

    records: List[Dict[str, Any]] = []

    # Пакетная загрузка детальной информации о треках
    for start_idx in range(0, total_tracks, batch_size):
        end_idx = min(start_idx + batch_size, total_tracks)
        batch = track_ids[start_idx:end_idx]

        if progress_callback:
            pct = int((start_idx / total_tracks) * 100)
            progress_callback(
                pct,
                100,
                f"Загрузка метаданных треков {start_idx + 1}–{end_idx} из {total_tracks:,}...",
            )

        try:
            full_tracks = client.tracks(batch)
        except Exception:
            full_tracks = []

        # Словарь для быстрого сопоставления по ID
        track_map = {str(t.id): t for t in full_tracks if t and t.id}

        for local_offset, t_id_raw in enumerate(batch):
            global_idx = start_idx + local_offset + 1
            t_id_str = str(t_id_raw)
            t = track_map.get(t_id_str)

            if not t:
                # Если метаданные недоступны
                records.append(
                    {
                        "id": global_idx,
                        "track_id": t_id_str,
                        "album_id": "",
                        "artist_raw": "Неизвестный исполнитель",
                        "title_raw": f"Трек {t_id_str}",
                        "duration_sec": 0,
                        "duration_fmt": "0:00",
                        "primary_artist": "Неизвестный исполнитель",
                        "all_artists": ["Неизвестный исполнитель"],
                        "artists_count": 1,
                        "is_collab": False,
                        "cover_uri": "",
                        "yandex_url": f"https://music.yandex.ru/track/{t_id_str}",
                    }
                )
                continue

            artist_names = [a.name for a in t.artists if a and a.name]
            artist_raw = ", ".join(artist_names) if artist_names else "Неизвестный артист"

            title_raw = t.title or "Без названия"
            if t.version:
                title_raw += f" ({t.version})"

            dur_sec = round((t.duration_ms or 0) / 1000)
            dur_fmt = f"{dur_sec // 60}:{dur_sec % 60:02d}"

            # Извлечение фитов и соавторов
            extracted_artists = extract_artists(artist_raw, title_raw)
            combined_artists = list(dict.fromkeys(artist_names + extracted_artists))
            if not combined_artists:
                combined_artists = [artist_raw]

            primary_artist = combined_artists[0]
            is_collab = len(combined_artists) > 1

            album_id = str(t.albums[0].id) if t.albums else ""
            cover_uri = ""
            if t.cover_uri:
                cover_uri = f"https://{t.cover_uri.replace('%%', '200x200')}"

            yandex_url = (
                f"https://music.yandex.ru/album/{album_id}/track/{t.id}"
                if album_id
                else f"https://music.yandex.ru/track/{t.id}"
            )

            records.append(
                {
                    "id": global_idx,
                    "track_id": str(t.id),
                    "album_id": album_id,
                    "artist_raw": artist_raw,
                    "title_raw": title_raw,
                    "duration_sec": dur_sec,
                    "duration_fmt": dur_fmt,
                    "primary_artist": primary_artist,
                    "all_artists": combined_artists,
                    "artists_count": len(combined_artists),
                    "is_collab": is_collab,
                    "cover_uri": cover_uri,
                    "yandex_url": yandex_url,
                }
            )

    if progress_callback:
        progress_callback(100, 100, "Коллекция успешно загружена!")

    df = pd.DataFrame(records)
    return df


def create_remote_playlist(
    client: Client,
    title: str,
    tracks: List[Dict[str, Any]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    batch_size: int = 250,
) -> Tuple[bool, str, Optional[str]]:
    """Создаёт плейлист в аккаунте Яндекс Музыки и наполняет его треками."""
    if not tracks:
        return False, "Список треков пуст.", None

    try:
        if progress_callback:
            progress_callback(0, 100, f"Создание плейлиста '{title}' в Яндекс Музыке...")

        # Вспомогательная функция очистки числовых ID
        def _clean_id(val: Any) -> Optional[str]:
            if val is None or pd.isna(val):
                return None
            s = str(val).strip()
            if not s or s.lower() in ("nan", "none"):
                return None
            if s.endswith(".0"):
                s = s[:-2]
            return s if s.isdigit() and int(s) > 0 else None

        # 1. Отбираем треки с валидными track_id и проверяем наличие album_id
        items_with_album = []
        missing_album_track_ids = []

        for t in tracks:
            t_id = _clean_id(t.get("track_id"))
            if not t_id:
                continue
            alb_id = _clean_id(t.get("album_id"))
            if alb_id:
                items_with_album.append({"id": t_id, "album_id": alb_id})
            else:
                missing_album_track_ids.append(t_id)

        # 2. Если есть треки без album_id, пробуем восстановить их альбомы через клиент Яндекса
        recovered_albums = {}
        if missing_album_track_ids:
            chunk_size = 100
            for i in range(0, len(missing_album_track_ids), chunk_size):
                chunk = missing_album_track_ids[i : i + chunk_size]
                try:
                    fetched = client.tracks(chunk)
                    for f_t in fetched:
                        if f_t and f_t.albums and len(f_t.albums) > 0 and f_t.albums[0].id:
                            f_alb = _clean_id(f_t.albums[0].id)
                            if f_alb:
                                recovered_albums[str(f_t.id)] = f_alb
                except Exception:
                    pass

        # 3. Собираем итоговый список треков, строго исключая треки без album_id
        # (иначе Яндекс возвращает 'wrong-json' из-за пустого значения albumId)
        final_valid_items = list(items_with_album)
        for t_id in missing_album_track_ids:
            rec_alb = recovered_albums.get(t_id)
            if rec_alb:
                final_valid_items.append({"id": t_id, "album_id": rec_alb})

        if not final_valid_items:
            return (
                False,
                "В списке отсутствуют треки с доступными альбомами (возможно, треки удалены из каталога Яндекс Музыки).",
                None,
            )

        skipped_count = len(tracks) - len(final_valid_items)

        # 4. Создаём пустой публичный плейлист
        playlist = client.users_playlists_create(title=title, visibility="public")
        if not playlist:
            return False, "Не удалось создать плейлист на сервере Яндекса.", None

        kind = playlist.kind
        user_id = client.account_uid
        revision = playlist.revision or 1

        total_tracks = len(final_valid_items)
        inserted_count = 0

        # 5. Пакетное добавление треков через Difference
        for start_idx in range(0, total_tracks, batch_size):
            end_idx = min(start_idx + batch_size, total_tracks)
            batch = final_valid_items[start_idx:end_idx]

            diff = Difference().add_insert(at=inserted_count, tracks=batch)

            if progress_callback:
                pct = int((start_idx / total_tracks) * 100)
                progress_callback(
                    pct,
                    100,
                    f"Добавление треков {start_idx + 1}–{end_idx} из {total_tracks} в плейлист...",
                )

            res = client.users_playlists_change(
                kind=kind,
                diff=diff.to_json(),
                revision=revision,
                user_id=user_id,
            )
            if res and res.revision:
                revision = res.revision
            inserted_count += len(batch)

        playlist_url = f"https://music.yandex.ru/users/{user_id}/playlists/{kind}"
        if progress_callback:
            progress_callback(100, 100, "Плейлист готов!")

        msg = f"Плейлист '{title}' успешно создан ({inserted_count} треков)!"
        if skipped_count > 0:
            msg += f" (Пропущено {skipped_count} заблокированных/удалённых треков)"

        return True, msg, playlist_url

    except Exception as err:
        return False, f"Ошибка при создании плейлиста в Яндекс Музыке: {err}", None
