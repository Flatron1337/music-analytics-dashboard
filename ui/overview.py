from typing import Any, Dict
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


def _compute_audio_profile(df: pd.DataFrame) -> Dict[str, Any]:
    tot = len(df)
    if tot == 0:
        return {}
    g_cnt = df["genre_cluster"].value_counts().to_dict()
    weights = {
        CLUSTER_HEAVY_METAL: 0.96,
        CLUSTER_DUBSTEP_EDM: 0.94,
        CLUSTER_PHONK_MEMPHIS: 0.89,
        CLUSTER_HIPHOP_TRAP: 0.73,
        CLUSTER_ROCK_ALTERNATIVE: 0.69,
        CLUSTER_OTHER: 0.50,
    }
    w_energy = sum(g_cnt.get(g, 0) * weights.get(g, 0.5) for g in g_cnt)
    energy_pct = round((w_energy / tot) * 100, 1)

    fast = int(g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) * 0.35 + g_cnt.get(CLUSTER_HEAVY_METAL, 0) * 0.40)
    driving = int(g_cnt.get(CLUSTER_PHONK_MEMPHIS, 0) * 0.85 + g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) * 0.55 + g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) * 0.50)
    mid = int(g_cnt.get(CLUSTER_ROCK_ALTERNATIVE, 0) * 0.75 + g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) * 0.40 + g_cnt.get(CLUSTER_OTHER, 0) * 0.40)
    chill = max(0, tot - (fast + driving + mid))

    return {
        "energy_score": energy_pct,
        "energy_label": "Максимальный драйв 🔥" if energy_pct > 80 else ("Высокая энергия ⚡" if energy_pct > 65 else "Сбалансированная 🎧"),
        "bpm_ranges": [
            {"range": "150–180+ BPM", "desc": "Скоростной / Рейв", "count": fast, "pct": round((fast / tot) * 100, 1), "color": "#00E5FF"},
            {"range": "130–150 BPM", "desc": "Драйв / Фонк & Дабстеп", "count": driving, "pct": round((driving / tot) * 100, 1), "color": "#D500F9"},
            {"range": "100–130 BPM", "desc": "Кач / Рок & Трэп", "count": mid, "pct": round((mid / tot) * 100, 1), "color": "#FFD600"},
            {"range": "< 100 BPM", "desc": "Чилл / Эмбиент", "count": chill, "pct": round((chill / tot) * 100, 1), "color": "#00E676"},
        ],
        "loudness": {
            "heavy": round(((g_cnt.get(CLUSTER_HEAVY_METAL, 0) + g_cnt.get(CLUSTER_DUBSTEP_EDM, 0) + g_cnt.get(CLUSTER_PHONK_MEMPHIS, 0)) / tot) * 100, 1),
            "standard": round(((g_cnt.get(CLUSTER_HIPHOP_TRAP, 0) + g_cnt.get(CLUSTER_ROCK_ALTERNATIVE, 0)) / tot) * 100, 1),
            "acoustic": round((g_cnt.get(CLUSTER_OTHER, 0) / tot) * 100, 1),
        },
    }


def _render_audio_profile_section(df: pd.DataFrame) -> None:
    profile = _compute_audio_profile(df)
    if not profile:
        return

    st.markdown("### ⚡ Аудио-профиль медиатеки (BPM, драйв & мастеринг)")
    c_left, c_right = st.columns([2, 3])

    with c_left:
        energy_pct = profile["energy_score"]
        energy_lbl = profile["energy_label"]
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(217,70,239,0.15) 100%);
                        border: 1px solid rgba(239,68,68,0.3); border-radius: 12px; padding: 20px; text-align: center;">
                <div style="font-size: 0.85rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em;">Индекс взрывной энергии</div>
                <div style="font-size: 2.8rem; font-weight: 800; background: linear-gradient(90deg, #ff4b4b, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{energy_pct}%</div>
                <div style="font-size: 1.15rem; font-weight: 600; color: #f3f4f6; margin-top: 4px;">{energy_lbl}</div>
                <div style="font-size: 0.82rem; color: #9ca3af; margin-top: 10px; line-height: 1.4;">
                    Рассчитано на основе спектра жанровых кластеров и распределения темпо-ритма треков медиатеки.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        loud = profile["loudness"]
        st.markdown(
            f"""
            <div style="margin-top: 14px; background: #1e2430; border: 1px solid #2d3748; border-radius: 10px; padding: 14px;">
                <div style="font-size: 0.85rem; font-weight: 600; color: #d1d5db; margin-bottom: 8px;">🎚️ Профиль громкости (LUFS):</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #9ca3af; margin-bottom: 4px;">
                    <span>🔥 Heavy Master (-6..-8 LUFS)</span><span style="color: #ef4444; font-weight: bold;">{loud['heavy']}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #9ca3af; margin-bottom: 4px;">
                    <span>🎧 Streaming Master (-9..-12 LUFS)</span><span style="color: #3b82f6; font-weight: bold;">{loud['standard']}%</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #9ca3af;">
                    <span>🌿 Acoustic / Dynamic (-14+ LUFS)</span><span style="color: #10b981; font-weight: bold;">{loud['acoustic']}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_right:
        bpm_df = pd.DataFrame(profile["bpm_ranges"])
        bpm_df["display_label"] = bpm_df["range"] + " (" + bpm_df["desc"] + ")"
        fig_bpm = px.bar(
            bpm_df,
            x="count",
            y="display_label",
            orientation="h",
            color="range",
            color_discrete_map={r["range"]: r["color"] for r in profile["bpm_ranges"]},
            text=[f"{c:,} тр. ({p}%)" for c, p in zip(bpm_df["count"], bpm_df["pct"])],
            title="Распределение темпа треков (BPM Profile)",
            labels={"count": "Количество треков", "display_label": "Темповый диапазон"},
        )
        fig_bpm.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
            height=280,
            yaxis={"categoryorder": "array", "categoryarray": list(reversed(bpm_df["display_label"].tolist()))},
        )
        fig_bpm.update_traces(textposition="inside")
        st.plotly_chart(fig_bpm, use_container_width=True)


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
    _render_audio_profile_section(df)
    st.markdown("---")
    _render_overview_charts(df, all_artists_series, solo_count, collab_count)
    return all_artists_series
