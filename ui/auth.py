import logging
import os
from typing import Optional, Tuple
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from yandex_api import (
    fetch_user_likes_df,
    login_yandex,
    poll_yandex_device_token,
    request_yandex_device_code,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_CACHE_FILE = os.path.join(BASE_DIR, ".yandex_token")
SYNCED_LIKES_CACHE = os.path.join(BASE_DIR, "synced_likes.pkl")


def sync_browser_storage(token: Optional[str] = None) -> None:
    """Синхронизирует токен с localStorage браузера."""
    if token:
        js = f"""
        <script>
            try {{ localStorage.setItem('yandex_music_token', '{token}'); }} catch (e) {{}}
        </script>
        """
    else:
        js = """
        <script>
            try {
                const saved = localStorage.getItem('yandex_music_token');
                const urlParams = new URLSearchParams(window.parent.location.search);
                if (saved && !urlParams.get('token')) {
                    urlParams.set('token', saved);
                    window.parent.location.search = urlParams.toString();
                }
            } catch (e) {}
        </script>
        """
    components.html(js, height=0, width=0)


def clear_browser_storage() -> None:
    """Очищает токен из localStorage браузера при выходе."""
    js = """
    <script>
        try { localStorage.removeItem('yandex_music_token'); } catch (e) {}
    </script>
    """
    components.html(js, height=0, width=0)


def _save_token_cache(token: str) -> None:
    try:
        with open(TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(token)
    except OSError as e:
        logger.debug("Could not write token cache file: %s", e)


def _clear_token_cache() -> None:
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            os.remove(TOKEN_CACHE_FILE)
        except OSError as e:
            logger.debug("Could not remove token cache file: %s", e)


def _read_token_cache() -> Optional[str]:
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    try:
        with open(TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip()
            return val if val else None
    except OSError as e:
        logger.debug("Could not read token cache file: %s", e)
        return None


def restore_cached_auth() -> None:
    """Восстановление авторизации из query_params, кэш-файла или localStorage."""
    if "yandex_client" in st.session_state:
        return

    token_candidate = None
    if "token" in st.query_params:
        p_val = st.query_params.get("token")
        if p_val and str(p_val).strip():
            token_candidate = str(p_val).strip()

    if not token_candidate:
        token_candidate = _read_token_cache()

    if not token_candidate:
        sync_browser_storage(None)
        return

    client, user_info, _ = login_yandex(token_candidate)
    if client and user_info:
        st.session_state["yandex_client"] = client
        st.session_state["yandex_user"] = user_info
        st.session_state["yandex_token"] = token_candidate
        st.query_params["token"] = token_candidate
        _save_token_cache(token_candidate)
        sync_browser_storage(token_candidate)
    else:
        st.query_params.pop("token", None)
        _clear_token_cache()
        clear_browser_storage()


def _render_device_login() -> None:
    st.sidebar.markdown("#### 🔑 Вход в Яндекс ID")
    st.sidebar.write("Самый простой и безопасный способ — авторизация по коду:")

    if "device_auth_data" not in st.session_state:
        if st.sidebar.button("📱 Получить код для ya.ru/device", type="primary", use_container_width=True):
            with st.sidebar.status("Запрос кода у Яндекса..."):
                d_data, d_err = request_yandex_device_code()
            if d_err:
                st.sidebar.error(d_err)
            else:
                st.session_state["device_auth_data"] = d_data
                st.rerun()
        return

    d_data = st.session_state["device_auth_data"]
    st.sidebar.markdown(f"1. Перейдите по ссылке: **[ya.ru/device]({d_data['verification_url']})**")
    st.sidebar.markdown("2. Введите этот код подтверждения:")
    st.sidebar.code(d_data["user_code"], language="text")

    col_chk, col_cancel = st.sidebar.columns(2)
    if col_chk.button("✅ Я ввёл код", type="primary", use_container_width=True):
        with st.sidebar.status("Проверка авторизации..."):
            token, poll_err = poll_yandex_device_token(d_data["device_code"])
        if token:
            client, user_info, err = login_yandex(token)
            if err:
                st.sidebar.error(err)
            else:
                st.session_state["yandex_client"] = client
                st.session_state["yandex_user"] = user_info
                st.session_state["yandex_token"] = token
                st.session_state.pop("device_auth_data", None)
                st.query_params["token"] = token
                _save_token_cache(token)
                sync_browser_storage(token)
                st.sidebar.success(f"Добро пожаловать, {user_info['full_name']}!")
                st.rerun()
        else:
            st.sidebar.warning(poll_err or "Код ещё не подтверждён на ya.ru/device.")

    if col_cancel.button("Отмена", use_container_width=True):
        st.session_state.pop("device_auth_data", None)
        st.rerun()


def _render_manual_login() -> None:
    with st.sidebar.expander("Или ввести OAuth-токен вручную"):
        token_input = st.text_input(
            "Токен Яндекс ID:",
            type="password",
            placeholder="y0_AgAAAA...",
            key="manual_token_inp",
            help="Ваш персональный OAuth-токен, если он уже у вас есть.",
        )
        if st.button("Войти по токену", use_container_width=True):
            clean_tok = token_input.strip()
            if not clean_tok:
                st.warning("Пожалуйста, введите токен.")
                return
            with st.status("Проверка токена..."):
                client, user_info, err = login_yandex(clean_tok)
            if err:
                st.error(err)
            else:
                st.session_state["yandex_client"] = client
                st.session_state["yandex_user"] = user_info
                st.session_state["yandex_token"] = clean_tok
                st.session_state.pop("device_auth_data", None)
                st.query_params["token"] = clean_tok
                _save_token_cache(clean_tok)
                sync_browser_storage(clean_tok)
                st.rerun()


def _render_user_profile(user_info: dict, account_uid_str: str) -> None:
    prof_col1, prof_col2 = st.sidebar.columns([1, 3])
    with prof_col1:
        if user_info.get("avatar_url"):
            st.image(user_info["avatar_url"], width=54)
        else:
            st.markdown("🎧")
    with prof_col2:
        st.markdown(f"**{user_info['full_name']}**")
        st.caption(f"ID: `{account_uid_str}` • 🟢 Онлайн")


def _perform_likes_sync(client: object) -> None:
    prog_bar = st.sidebar.progress(0)
    status_box = st.sidebar.empty()

    def update_progress(cur: int, tot: int, text: str) -> None:
        prog_bar.progress(min(1.0, cur / max(1, tot)))
        status_box.caption(text)

    with st.spinner("Загрузка треков из вашей Яндекс Музыки..."):
        df_loaded = fetch_user_likes_df(client, progress_callback=update_progress)
    prog_bar.empty()
    status_box.empty()

    if not df_loaded.empty:
        st.session_state["yandex_likes_df"] = df_loaded
        try:
            df_loaded.to_pickle(SYNCED_LIKES_CACHE)
        except (IOError, OSError, ValueError) as e:
            logger.debug("Could not save likes cache: %s", e)
        st.sidebar.success(f"Синхронизировано: {len(df_loaded):,} треков!")


def _load_cached_likes_if_needed() -> None:
    if "yandex_likes_df" in st.session_state:
        return
    if os.path.exists(SYNCED_LIKES_CACHE):
        try:
            df_cached = pd.read_pickle(SYNCED_LIKES_CACHE)
            if df_cached is not None and not df_cached.empty:
                st.session_state["yandex_likes_df"] = df_cached
        except (IOError, OSError, ValueError, KeyError) as e:
            logger.debug("Could not load cached likes: %s", e)


def _render_local_file_upload() -> Tuple[pd.DataFrame, str]:
    st.sidebar.markdown("---")
    uploaded = st.sidebar.file_uploader(
        "Загрузить файл плейлиста (.txt)",
        type=["txt"],
        help="Формат: <ID>. <Артист> - <Название> [<длительность>]",
    )
    if uploaded is not None:
        from parser import parse_playlist_text
        content = uploaded.getvalue().decode("utf-8", errors="replace")
        return parse_playlist_text(content), uploaded.name
    st.markdown("### 📁 Анализ локального плейлиста")
    st.info("Загрузите текстовый файл с экспортом плейлиста (.txt) через боковую панель слева.")
    return pd.DataFrame(), ""


def handle_sidebar_auth() -> Tuple[pd.DataFrame, str, bool, str]:
    """Управление авторизацией и источником данных в сайдбаре."""
    restore_cached_auth()
    st.sidebar.title("🎛️ Источник данных")
    has_active_yandex = "yandex_client" in st.session_state

    source_mode = st.sidebar.radio(
        "Режим работы:",
        ("🟡 Яндекс Музыка (Live API)", "📁 Локальный файл (.txt)"),
        index=0,
    )

    df_raw = pd.DataFrame()
    source_name = ""
    account_uid_str = "965180470"

    if source_mode == "🟡 Яндекс Музыка (Live API)":
        st.sidebar.markdown("---")
        if not has_active_yandex:
            _render_device_login()
            _render_manual_login()
            st.markdown("### 👋 Добро пожаловать в Музыкальный Дашборд")
            st.info("💡 Войдите в свой **Яндекс ID** в боковой панели слева для анализа медиатеки.")
            return df_raw, source_name, False, account_uid_str

        user_info = st.session_state["yandex_user"]
        client = st.session_state["yandex_client"]
        account_uid_str = str(user_info.get("uid") or account_uid_str)
        _render_user_profile(user_info, account_uid_str)

        col_btn_sync, col_btn_logout = st.sidebar.columns(2)
        sync_btn = col_btn_sync.button("🔄 Обновить", use_container_width=True)
        if col_btn_logout.button("🚪 Выйти", use_container_width=True):
            st.session_state.pop("yandex_client", None)
            st.session_state.pop("yandex_user", None)
            st.session_state.pop("yandex_token", None)
            st.session_state.pop("yandex_likes_df", None)
            st.query_params.pop("token", None)
            _clear_token_cache()
            clear_browser_storage()
            st.rerun()

        if not sync_btn:
            _load_cached_likes_if_needed()
        if sync_btn or "yandex_likes_df" not in st.session_state:
            _perform_likes_sync(client)

        if "yandex_likes_df" in st.session_state:
            df_raw = st.session_state["yandex_likes_df"]
            source_name = f"Яндекс Музыка ({user_info['login']})"
    else:
        df_raw, source_name = _render_local_file_upload()

    return df_raw, source_name, has_active_yandex, account_uid_str

