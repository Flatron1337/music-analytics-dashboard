import urllib.parse
from typing import List, Tuple
import pandas as pd
import plotly.express as px
import streamlit as st

from genre_classifier import (
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
)
from parser import format_seconds
from yandex_api import create_remote_playlist

CLUSTER_KEYS: List[Tuple[str, str, str]] = [
    (CLUSTER_HEAVY_METAL, "Плейлист_Heavy_Metal", "🎸"),
    (CLUSTER_DUBSTEP_EDM, "Плейлист_Dubstep_EDM", "🔊"),
    (CLUSTER_PHONK_MEMPHIS, "Плейлист_Phonk_Memphis", "💀"),
    (CLUSTER_HIPHOP_TRAP, "Плейлист_HipHop_Trap", "🎤"),
    (CLUSTER_ROCK_ALTERNATIVE, "Плейлист_Rock_Alternative", "⚡"),
    (CLUSTER_OTHER, "Плейлист_Other_Electronic", "🔀"),
]

COLOR_MAP = {
    CLUSTER_HEAVY_METAL: "#ef4444",
    CLUSTER_DUBSTEP_EDM: "#06b6d4",
    CLUSTER_PHONK_MEMPHIS: "#a855f7",
    CLUSTER_HIPHOP_TRAP: "#f59e0b",
    CLUSTER_ROCK_ALTERNATIVE: "#10b981",
    CLUSTER_OTHER: "#6b7280",
}


def _render_genre_charts(df: pd.DataFrame) -> None:
    genre_counts = df["genre_cluster"].value_counts().reset_index()
    genre_counts.columns = ["Кластер", "Треков"]
    genre_counts["Процент"] = (genre_counts["Треков"] / len(df) * 100).round(1)

    g_col1, g_col2 = st.columns([3, 2])
    with g_col1:
        fig_bar = px.bar(
            genre_counts,
            x="Кластер",
            y="Треков",
            color="Кластер",
            text="Треков",
            title="Распределение треков по жанровым направлениям",
            color_discrete_map=COLOR_MAP,
        )
        fig_bar.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20), height=380)
        st.plotly_chart(fig_bar, use_container_width=True)

    with g_col2:
        fig_pie = px.pie(
            genre_counts,
            names="Кластер",
            values="Треков",
            hole=0.45,
            title="Доли направлений в коллекции",
            color="Кластер",
            color_discrete_map=COLOR_MAP,
        )
        fig_pie.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
        st.plotly_chart(fig_pie, use_container_width=True)


def _render_single_cluster_downloads(c_name: str, file_base: str, emoji: str, c_tracks: pd.DataFrame) -> None:
    total_time = format_seconds(int(c_tracks["duration_sec"].sum()))
    st.markdown(f"**{emoji} {c_name}**")
    st.caption(f"{len(c_tracks):,} треков • {total_time}")

    records = c_tracks.to_dict(orient="records")
    txt_content = "".join(f"{i}. {r['artist_raw']} - {r['title_raw']} [{r['duration_fmt']}]\n" for i, r in enumerate(records, 1))
    st.download_button(label="📄 TXT", data=txt_content, file_name=f"{file_base}.txt", mime="text/plain", key=f"dl_txt_{c_name}")

    m3u8_content = "#EXTM3U\n" + "".join(
        f"#EXTINF:{r['duration_sec']},{r['artist_raw']} - {r['title_raw']}\n{r['artist_raw']} - {r['title_raw']}.mp3\n"
        for r in records
    )
    st.download_button(label="🎶 M3U8", data=m3u8_content, file_name=f"{file_base}.m3u8", mime="application/x-mpegURL", key=f"dl_m3u8_{c_name}")

    ym_content = "".join(f"{r['artist_raw']} - {r['title_raw']}\n" for r in records)
    st.download_button(label="🟡 Яндекс", data=ym_content, file_name=f"{file_base}_ym.txt", mime="text/plain", key=f"dl_ym_{c_name}")

    if "yandex_client" in st.session_state:
        if any(r.get("track_id") and str(r["track_id"]).isdigit() for r in records):
            if st.button("🪄 В Яндекс", key=f"btn_cloud_{c_name}", help=f"Создать '{c_name}' в аккаунте"):
                with st.spinner(f"Создаем плейлист «{c_name}»..."):
                    ok, msg, pl_url = create_remote_playlist(
                        client=st.session_state["yandex_client"],
                        title=f"Моя Музыка: {c_name}",
                        tracks=records,
                    )
                if ok:
                    st.success(msg)
                    if pl_url:
                        st.markdown(f"[🔗 Открыть созданный плейлист]({pl_url})")
                    st.balloons()
                else:
                    st.error(msg)


def _render_download_section(df: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### 📥 Скачать готовые узкопрофильные плейлисты")
    dl_cols = st.columns(len(CLUSTER_KEYS))
    for i, (c_name, file_base, emoji) in enumerate(CLUSTER_KEYS):
        c_tracks = df[df["genre_cluster"] == c_name]
        with dl_cols[i]:
            _render_single_cluster_downloads(c_name, file_base, emoji, c_tracks)

    if "yandex_client" in st.session_state:
        st.success("✨ **Вы авторизованы через Яндекс ID!** Создавайте плейлисты кнопкой **«🪄 В Яндекс»**.")
    else:
        st.info("💡 **Создание в Яндекс Музыке:** подключите аккаунт в сайдбаре или скачайте файл кнопкой **«🟡 Яндекс»**.")


def _render_genre_explorer(df: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### 🔍 Исследование треков конкретного жанра")
    selected_genre = st.selectbox("Выберите жанр:", [k[0] for k in CLUSTER_KEYS])
    sub_df = df[df["genre_cluster"] == selected_genre]

    sub_top = sub_df.explode("all_artists")["all_artists"].value_counts().head(15).reset_index()
    sub_top.columns = ["Артист", "Треков в жанре"]
    st.markdown(f"**Топ артистов в категории {selected_genre}:**")
    st.dataframe(sub_top, use_container_width=True, hide_index=True)

    st.markdown(f"**Список треков ({len(sub_df):,}):**")
    sub_table = sub_df[["id", "artist_raw", "title_raw", "duration_fmt"]].copy().rename(
        columns={"id": "№", "artist_raw": "Исполнитель", "title_raw": "Название", "duration_fmt": "Длительность"}
    )
    sub_table["yandex_url"] = [
        f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(f'{a} {t}')}"
        for a, t in zip(sub_df["artist_raw"], sub_df["title_raw"])
    ]
    st.dataframe(
        sub_table,
        column_config={"yandex_url": st.column_config.LinkColumn("Яндекс Музыка", display_text="Слушать ↗")},
        use_container_width=True,
        hide_index=True,
    )


def render_genres_tab(df: pd.DataFrame) -> None:
    """Отображает вкладку кластеризации жанров и экспорта плейлистов."""
    st.markdown("### 🎸 Автоматическая кластеризация по жанрам")
    st.write("Коллекция распределена по ключевым жанровым направлениям на основе базы знаний и тегов.")
    _render_genre_charts(df)
    _render_download_section(df)
    _render_genre_explorer(df)
