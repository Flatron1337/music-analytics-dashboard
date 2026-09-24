import os
import pandas as pd
import streamlit as st

from genre_classifier import GenreClassifier
from parser import load_playlist
from ui.ai_widget import render_ai_enrichment_widget, render_mobile_app_card
from ui.auth import handle_sidebar_auth
from ui.catalog import render_duration_tab, render_search_tab
from ui.duplicates import render_duplicates_tab
from ui.genres import render_genres_tab
from ui.graph import render_graph_tab
from ui.overview import render_overview_tab
from ui.timeline import render_timeline_tab

DEFAULT_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "Мне нравится_965180470_20260915_213456.txt"
)

st.set_page_config(
    page_title="Музыкальный дашборд | Анализ плейлиста",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #ff4b4b 0%, #ff8533 50%, #facc15 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        color: #9ca3af;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #1e2430;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #f3f4f6;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.6rem;
        }
        .sub-title {
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        .metric-card {
            padding: 10px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 1.35rem;
        }
        .metric-label {
            font-size: 0.75rem;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_cached_playlist_from_file(file_path: str) -> pd.DataFrame:
    return load_playlist(file_path)


@st.cache_data(show_spinner=False)
def get_cached_genres(_df: pd.DataFrame, dataset_fingerprint: str) -> pd.Series:
    classifier = GenreClassifier()
    clusters = []
    for _, row in _df.iterrows():
        cluster, _ = classifier.classify_track(
            artist_raw=row["artist_raw"],
            title_raw=row["title_raw"],
            all_artists=row["all_artists"],
            allow_network=False,
        )
        clusters.append(cluster)
    return pd.Series(clusters, index=_df.index)


def _setup_ordered_dataframe(df_raw: pd.DataFrame, source_name: str) -> pd.DataFrame:
    chrono_mode = st.sidebar.radio(
        "Порядок треков по времени:",
        (
            "№1 = Самый недавний (стандарт Яндекс Музыки)",
            "№1 = Самый первый (хронологический)",
        ),
        index=0,
    )
    df = df_raw.copy()
    if chrono_mode.startswith("№1 = Самый недавний"):
        df["time_order"] = len(df) - df["id"] + 1
    else:
        df["time_order"] = df["id"]

    dataset_fingerprint = f"{source_name}_{len(df)}"
    df["genre_cluster"] = get_cached_genres(df, dataset_fingerprint)
    return df


def _render_sidebar_meta(df: pd.DataFrame, source_name: str, has_active_yandex: bool, account_uid_str: str) -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(f"📁 Источник: **{source_name}**")
    st.sidebar.caption(f"🟡 Сервис: **Яндекс Музыка** {'(Live API 🟢)' if has_active_yandex else ''}")
    st.sidebar.caption(f"👤 ID профиля: **{account_uid_str}**")
    st.sidebar.caption(f"🎵 Всего треков: **{len(df):,}**")
    render_ai_enrichment_widget(df)
    render_mobile_app_card()


def main() -> None:
    df_raw, source_name, has_active_yandex, account_uid_str = handle_sidebar_auth()
    if df_raw.empty:
        st.stop()

    df = _setup_ordered_dataframe(df_raw, source_name)
    _render_sidebar_meta(df, source_name, has_active_yandex, account_uid_str)

    st.markdown('<div class="main-title">🎧 Анализ музыкального плейлиста</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-title">Глубокая интерактивная аналитика для <b>{len(df):,}</b> треков из <b>Яндекс Музыки</b></div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            "📊 Обзор (KPI)",
            "🎸 Жанры и плейлисты",
            "📈 Эволюция вкуса",
            "🕸️ Граф связей артистов",
            "⏱️ Хронометраж",
            "🔍 Каталог и поиск",
            "🧹 Дубликаты и ремастеры",
        ]
    )
    tab_ov, tab_gen, tab_time, tab_graph, tab_dur, tab_search, tab_dups = tabs

    with tab_ov:
        all_artists_series = render_overview_tab(df)
    with tab_gen:
        render_genres_tab(df)
    with tab_time:
        render_timeline_tab(df, all_artists_series)
    with tab_graph:
        render_graph_tab(df)
    with tab_dur:
        render_duration_tab(df, all_artists_series)
    with tab_search:
        render_search_tab(df)
    with tab_dups:
        render_duplicates_tab(df)


if __name__ == "__main__":
    main()
