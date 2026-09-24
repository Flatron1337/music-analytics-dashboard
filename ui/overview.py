import pandas as pd
import plotly.express as px
import streamlit as st

from parser import format_seconds


def _render_kpi_cards(
    total_tracks: int,
    unique_artists: int,
    total_sec: int,
    avg_sec: int,
) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{total_tracks:,}</div><div class="metric-label">Всего треков</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{unique_artists:,}</div><div class="metric-label">Уникальных артистов</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{format_seconds(total_sec)}</div><div class="metric-label">Общее время</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{avg_sec // 60}:{avg_sec % 60:02d}</div><div class="metric-label">Средняя длительность</div></div>',
            unsafe_allow_html=True,
        )


def _render_overview_charts(
    df: pd.DataFrame,
    all_artists_series: pd.Series,
    solo_count: int,
    collab_count: int,
) -> None:
    chart_col1, chart_col2 = st.columns([3, 2])
    with chart_col1:
        top_artists_df = all_artists_series.value_counts().head(20).reset_index()
        top_artists_df.columns = ["Исполнитель", "Количество треков"]

        fig_top = px.bar(
            top_artists_df,
            x="Количество треков",
            y="Исполнитель",
            orientation="h",
            color="Количество треков",
            color_continuous_scale="Viridis",
            title="Топ-20 исполнителей по количеству треков",
        )
        fig_top.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=20, r=20, t=40, b=20), height=520)
        st.plotly_chart(fig_top, use_container_width=True)

    with chart_col2:
        fig_collab = px.pie(
            names=["Соло-треки", "Коллаборации / Фиты"],
            values=[solo_count, collab_count],
            title="Соотношение: Соло vs Фиты",
            hole=0.45,
            color_discrete_sequence=["#3b82f6", "#f97316"],
        )
        fig_collab.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=250)
        st.plotly_chart(fig_collab, use_container_width=True)

        collab_artist_counts = (
            df[df["is_collab"]].explode("all_artists")["all_artists"].value_counts().head(10).reset_index()
        )
        collab_artist_counts.columns = ["Артист", "Фитов"]

        fig_collab_artists = px.bar(
            collab_artist_counts,
            x="Фитов",
            y="Артист",
            orientation="h",
            color="Фитов",
            color_continuous_scale="Oranges",
            title="Топ-10 артистов по числу совместных треков",
        )
        fig_collab_artists.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(l=20, r=20, t=40, b=20), height=250)
        st.plotly_chart(fig_collab_artists, use_container_width=True)


def render_overview_tab(df: pd.DataFrame) -> pd.Series:
    """Отображает вкладку с ключевыми метриками (KPI) и общими графиками."""
    all_artists_series = df.explode("all_artists")["all_artists"]
    unique_artists_count = all_artists_series.nunique()
    total_dur_sec = int(df["duration_sec"].sum())
    avg_dur_sec = int(df["duration_sec"].mean()) if len(df) > 0 else 0
    collab_count = int(df["is_collab"].sum())
    solo_count = len(df) - collab_count

    _render_kpi_cards(len(df), unique_artists_count, total_dur_sec, avg_dur_sec)
    st.markdown("###")
    _render_overview_charts(df, all_artists_series, solo_count, collab_count)
    return all_artists_series
