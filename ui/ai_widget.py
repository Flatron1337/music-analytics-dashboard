import io
import os
import time
from typing import Dict, List, Tuple
import pandas as pd
import qrcode
import streamlit as st

from ai_genre_classifier import AIGenreClassifier, _load_keys
import genre_db

DEFAULT_EXTERNAL_URL = os.getenv(
    "RENDER_EXTERNAL_URL", "https://music-analytics-dashboard.onrender.com"
)


def _render_qr_code(download_url: str) -> None:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(download_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#f3f4f6", back_color="#1e2430")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue(), caption="Наведите камеру телефона", use_container_width=True)


def render_mobile_app_card() -> None:
    """Отображает карточку скачивания Android APK с QR-кодом для смартфона."""
    st.sidebar.markdown("---")
    with st.sidebar.expander("📱 Мобильное приложение (Android)", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.85rem; color: #9ca3af; margin-bottom: 8px;">
                Полнофункциональный мобильный клиент на <b>Flutter</b> с оффлайн-кэшем и аудиоплеером.
            </div>
            """,
            unsafe_allow_html=True,
        )
        download_url = f"{DEFAULT_EXTERNAL_URL}/download/apk"
        _render_qr_code(download_url)
        st.link_button("📥 Скачать APK файл", download_url, use_container_width=True)


def _build_artist_tracks_lookup(df: pd.DataFrame) -> Dict[str, List[str]]:
    lookup: Dict[str, List[str]] = {}
    if df.empty or "all_artists" not in df.columns or "title_raw" not in df.columns:
        return lookup

    for _, row in df.iterrows():
        title = str(row.get("title_raw", "")).strip()
        artists = row.get("all_artists") or []
        for art in artists:
            key = str(art).strip().lower()
            if key:
                lookup.setdefault(key, []).append(title)
    return lookup


def _execute_ai_enrichment(
    targets: List[Tuple[str, str]],
    artist_tracks: Dict[str, List[str]],
    batch_size: int,
) -> int:
    ai_classifier = AIGenreClassifier()
    progress_bar = st.sidebar.progress(0.0)
    status_text = st.sidebar.empty()
    total = len(targets)
    saved_count = 0

    for i in range(0, total, batch_size):
        chunk = targets[i : i + batch_size]
        payload = [
            {"artist": name, "tracks": artist_tracks.get(key, [])[:4]}
            for key, name in chunk
        ]
        status_text.caption(f"🧠 Анализ {i + 1}–{min(i + batch_size, total)} из {total}...")
        try:
            results = ai_classifier._call_gemini_batch(payload)
            db_batch = [
                (r["artist"], r["cluster"], r.get("tags", []), "ai_gemini")
                for r in results
                if "artist" in r and "cluster" in r
            ]
            saved_count += genre_db.save_cached_artists_batch(db_batch)
        except Exception as err:
            status_text.warning(f"Ошибка пакета: {err}")

        progress_bar.progress(min(1.0, (i + len(chunk)) / total))
        time.sleep(1.0)

    progress_bar.empty()
    status_text.empty()
    return saved_count


def render_ai_enrichment_widget(df: pd.DataFrame) -> None:
    """Виджет в сайдбаре для мониторинга и запуска AI-обогащения жанров."""
    st.sidebar.markdown("---")
    with st.sidebar.expander("🤖 ИИ-Классификатор жанров", expanded=False):
        stats = genre_db.get_db_stats()
        backend_name = "PostgreSQL (Render)" if stats["backend"] == "postgresql" else "SQLite (Local)"
        st.caption(f"🗄️ База данных: **{backend_name}**")
        st.caption(f"📊 Всего в кэше: **{stats['total']:,}** артистов")
        st.caption(f"✨ Размечено ИИ: **{stats['ai_enriched']:,}**")
        st.caption(f"⏳ Ожидает разметки: **{stats['unresolved']:,}**")

        gemini_k, groq_k = _load_keys()
        if not gemini_k and not groq_k:
            st.warning("⚠️ API-ключи Gemini/Groq не обнаружены в .ai_keys.json или переменных окружения.")
            return

        unresolved = genre_db.fetch_unresolved_artists()
        if not unresolved:
            st.success("✅ Все артисты в библиотеке уже классифицированы!")
            return

        st.markdown(f"Найдено неразмеченных: **{len(unresolved):,}**")
        batch_limit = st.slider("Сколько обработать за запуск:", 5, min(100, len(unresolved)), min(25, len(unresolved)), 5)

        if st.button("⚡ Запустить AI-обогащение", use_container_width=True):
            artist_tracks = _build_artist_tracks_lookup(df)
            to_process = unresolved[:batch_limit]
            with st.spinner("Работа нейросети Gemini..."):
                saved = _execute_ai_enrichment(to_process, artist_tracks, batch_size=15)
            st.success(f"🎉 Успешно размечено и сохранено: {saved} артистов!")
            st.rerun()
