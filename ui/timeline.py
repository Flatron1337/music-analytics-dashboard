import pandas as pd
import plotly.express as px
import streamlit as st

from parser import calculate_timeline_segments


def _render_timeline_segments(df: pd.DataFrame) -> None:
    time_col1, time_col2 = st.columns(2)
    with time_col1:
        num_segments = st.slider("Количество временных отрезков:", 4, 16, 8, 1)
    with time_col2:
        top_n = st.slider("Сколько ключевых артистов отслеживать:", 4, 12, 7, 1)

    timeline_df = calculate_timeline_segments(
        df.sort_values("time_order"),
        num_segments=num_segments,
        top_n_artists=top_n,
    )
    fig_timeline = px.line(
        timeline_df,
        x="segment",
        y="count",
        color="artist",
        markers=True,
        title="Динамика количества треков топ-артистов по хронологическим эпохам",
        labels={"segment": "Временной интервал", "count": "Треков", "artist": "Артист"},
    )
    fig_timeline.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20), height=430)
    st.plotly_chart(fig_timeline, use_container_width=True)


def _render_duration_trend(df: pd.DataFrame) -> None:
    st.markdown("---")
    st.markdown("#### ⏳ Тренд длительности: становились ли треки короче?")
    rolling_window = st.slider("Размер скользящего окна сглаживания (треков):", 50, 500, 200, 50)
    df_sorted = df.sort_values("time_order").copy()
    df_sorted["rolling_duration"] = df_sorted["duration_sec"].rolling(window=rolling_window, min_periods=10).mean()

    fig_trend = px.line(
        df_sorted,
        x="time_order",
        y="rolling_duration",
        title=f"Скользящее среднее длительности треков (окно: {rolling_window} треков)",
        labels={"time_order": "Хронологический индекс", "rolling_duration": "Секунд"},
    )
    fig_trend.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
    st.plotly_chart(fig_trend, use_container_width=True)


def _render_artist_timeline(df: pd.DataFrame, all_artists_series: pd.Series) -> None:
    st.markdown("---")
    st.markdown("#### 🎯 Индивидуальный таймлайн конкретного артиста")
    popular_artists = all_artists_series.value_counts().head(200).index.tolist()
    selected_artist = st.selectbox("Выберите исполнителя:", popular_artists)
    if not selected_artist:
        return

    artist_mask = df["all_artists"].apply(lambda artists: selected_artist in artists if isinstance(artists, list) else False)
    artist_tracks = df[artist_mask].copy()

    fig_density = px.histogram(
        artist_tracks,
        x="time_order",
        nbins=40,
        title=f"Распределение добавления треков '{selected_artist}' (всего: {len(artist_tracks)})",
        labels={"time_order": "Порядковый номер в хронологии", "count": "Треков"},
        color_discrete_sequence=["#38bdf8"],
    )
    fig_density.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=320)
    st.plotly_chart(fig_density, use_container_width=True)


def render_timeline_tab(df: pd.DataFrame, all_artists_series: pd.Series) -> None:
    """Отображает вкладку эволюции музыкального вкуса по времени."""
    st.markdown("### 📈 Изменение вкуса по хронологии добавления")
    st.write("Анализ показывает, как менялись любимые артисты и средний хронометраж песен.")
    _render_timeline_segments(df)
    _render_duration_trend(df)
    _render_artist_timeline(df, all_artists_series)
