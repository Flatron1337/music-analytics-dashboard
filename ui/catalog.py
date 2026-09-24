from typing import Any, Dict, Optional
import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.genres import CLUSTER_KEYS


def _render_duration_charts(df: pd.DataFrame, all_artists_series: pd.Series) -> None:
    dur_col1, dur_col2 = st.columns([3, 2])
    with dur_col1:
        fig_hist = px.histogram(
            df,
            x="duration_sec",
            nbins=60,
            title="Распределение длительности треков (секунды)",
            labels={"duration_sec": "Длительность (сек)", "count": "Количество треков"},
            color_discrete_sequence=["#10b981"],
        )
        mean_sec = df["duration_sec"].mean()
        median_sec = df["duration_sec"].median()
        fig_hist.add_vline(x=mean_sec, line_dash="dash", line_color="#f59e0b", annotation_text=f"Среднее: {int(mean_sec//60)}:{int(mean_sec%60):02d}")
        fig_hist.add_vline(x=median_sec, line_dash="dot", line_color="#ef4444", annotation_text=f"Медиана: {int(median_sec//60)}:{int(median_sec%60):02d}")
        fig_hist.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=420)
        st.plotly_chart(fig_hist, use_container_width=True)

    with dur_col2:
        top_10_names = all_artists_series.value_counts().head(10).index.tolist()
        df_top10 = df[df["primary_artist"].isin(top_10_names)]
        fig_box = px.box(
            df_top10,
            x="primary_artist",
            y="duration_sec",
            title="Сравнение хронометража у Топ-10 артистов",
            labels={"primary_artist": "Артист", "duration_sec": "Секунды"},
            color="primary_artist",
        )
        fig_box.update_layout(showlegend=False, margin=dict(l=20, r=20, t=40, b=20), height=420)
        st.plotly_chart(fig_box, use_container_width=True)


def _render_shortest_longest_tables(df: pd.DataFrame) -> None:
    records_col1, records_col2 = st.columns(2)
    with records_col1:
        st.markdown("#### ⚡ Топ-15 самых коротких треков")
        short_df = (
            df.sort_values(by="duration_sec", ascending=True)
            .head(15)[["id", "artist_raw", "title_raw", "duration_fmt"]]
            .rename(columns={"id": "№", "artist_raw": "Исполнитель", "title_raw": "Трек", "duration_fmt": "Время"})
        )
        st.dataframe(short_df, use_container_width=True, hide_index=True)

    with records_col2:
        st.markdown("#### ⏳ Топ-15 самых длинных треков")
        long_df = (
            df.sort_values(by="duration_sec", ascending=False)
            .head(15)[["id", "artist_raw", "title_raw", "duration_fmt"]]
            .rename(columns={"id": "№", "artist_raw": "Исполнитель", "title_raw": "Трек", "duration_fmt": "Время"})
        )
        st.dataframe(long_df, use_container_width=True, hide_index=True)


def render_duration_tab(df: pd.DataFrame, all_artists_series: pd.Series) -> None:
    """Отображает вкладку анализа хронометража треков."""
    st.markdown("### ⏱️ Анализ длительности треков")
    _render_duration_charts(df, all_artists_series)
    st.markdown("---")
    _render_shortest_longest_tables(df)


def _filter_search_dataset(df: pd.DataFrame) -> pd.DataFrame:
    search_query = st.text_input("Поиск по артисту или названию:", placeholder="Например: Ghostemane, Phonk, Remix...")
    c1, c2, c3 = st.columns(3)
    with c1:
        genre_choice = st.selectbox("Фильтр по жанру:", ["Все жанры"] + [k[0] for k in CLUSTER_KEYS])
    with c2:
        only_collabs = st.checkbox("Только совместные треки (фиты)")
    with c3:
        max_dur = int(df["duration_sec"].max())
        selected_dur = st.slider("Длительность (секунды):", 0, max_dur, (0, max_dur), 10)

    filtered = df.copy()
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = filtered[filtered["artist_raw"].str.lower().str.contains(q) | filtered["title_raw"].str.lower().str.contains(q)]
    if genre_choice != "Все жанры":
        filtered = filtered[filtered["genre_cluster"] == genre_choice]
    if only_collabs:
        filtered = filtered[filtered["is_collab"]]
    filtered = filtered[(filtered["duration_sec"] >= selected_dur[0]) & (filtered["duration_sec"] <= selected_dur[1])]
    return filtered


def _render_search_results(filtered_df: pd.DataFrame, total_count: int) -> None:
    st.caption(f"Найдено треков: **{len(filtered_df):,}** из {total_count:,}")
    has_covers = "cover_uri" in filtered_df.columns and filtered_df["cover_uri"].astype(str).str.startswith("http").any()

    display_cols = ["id"] + (["cover_uri"] if has_covers else []) + ["artist_raw", "title_raw", "genre_cluster", "duration_fmt", "is_collab"]
    display_df = filtered_df[display_cols].copy().rename(
        columns={"id": "№", "cover_uri": "Обложка", "artist_raw": "Исполнитель", "title_raw": "Название", "genre_cluster": "Жанр", "duration_fmt": "Длительность", "is_collab": "Фит?"}
    )
    display_df["yandex_url"] = [
        f"https://music.yandex.ru/search?text={urllib.parse.quote_plus(f'{a} {t}')}"
        for a, t in zip(filtered_df["artist_raw"], filtered_df["title_raw"])
    ]

    cfg: Dict[str, Any] = {"yandex_url": st.column_config.LinkColumn("Яндекс Музыка", display_text="Слушать ↗")}
    if has_covers:
        cfg["Обложка"] = st.column_config.ImageColumn("Обложка")

    st.dataframe(display_df, column_config=cfg, use_container_width=True, hide_index=True)
    csv_data = display_df.drop(columns=["yandex_url"], errors="ignore").to_csv(index=False, encoding="utf-8-sig")
    st.download_button(label="📥 Скачать найденные треки в CSV", data=csv_data, file_name="filtered_music_tracks.csv", mime="text/csv")


def _fetch_track_stream_cached(
    track_id: str,
    artist: str,
    title: str,
    token: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    import yandex_api
    return yandex_api.get_track_stream_url(track_id, token=token, artist=artist, title=title)


def _render_track_audio_player(filtered_df: pd.DataFrame) -> None:
    if filtered_df.empty:
        return

    st.markdown("---")
    st.markdown("#### 🎧 Прослушать аудио-отрывок трека (Audio Preview)")
    sample_df = filtered_df.head(50)
    options = [f"№{r['id']} — {r['artist_raw']} — {r['title_raw']}" for _, r in sample_df.iterrows()]
    selected_option = st.selectbox(
        "Выберите трек для прослушивания (первые 50 из найденных):",
        options,
        key="preview_track_sel",
    )
    if not selected_option:
        return

    idx = options.index(selected_option)
    sel_row = sample_df.iloc[idx]
    col_btn, col_player = st.columns([1, 3])
    with col_btn:
        play_clicked = st.button("▶️ Загрузить превью", key=f"btn_play_{sel_row['id']}")

    if play_clicked:
        token = st.session_state.get("yandex_token") or None
        with st.spinner("Получение аудио-потока из Яндекс Музыки..."):
            stream_info = _fetch_track_stream_cached(
                str(sel_row["id"]),
                str(sel_row["artist_raw"]),
                str(sel_row["title_raw"]),
                token,
            )
        if stream_info and stream_info.get("stream_url"):
            with col_player:
                st.caption(f"Битрейт: {stream_info.get('bitrate', 192)} kbps ({stream_info.get('codec', 'mp3')})")
                st.audio(stream_info["stream_url"])
        else:
            with col_player:
                st.warning("Не удалось получить аудио-поток для этого трека (возможно, требуется авторизация с Плюсом).")


def render_search_tab(df: pd.DataFrame) -> None:
    """Отображает вкладку поиска и каталога треков."""
    st.markdown("### 🔍 Поиск и фильтрация треков")
    filtered = _filter_search_dataset(df)
    _render_search_results(filtered, len(df))
    _render_track_audio_player(filtered)
