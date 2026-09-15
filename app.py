import os
from typing import Dict, List, Optional
import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import streamlit as st

from genre_classifier import (
    CLUSTER_DUBSTEP_EDM,
    CLUSTER_HEAVY_METAL,
    CLUSTER_HIPHOP_TRAP,
    CLUSTER_OTHER,
    CLUSTER_PHONK_MEMPHIS,
    CLUSTER_ROCK_ALTERNATIVE,
    GenreClassifier,
)
from parser import (
    build_collaborations_graph,
    calculate_timeline_segments,
    format_seconds,
    load_playlist,
    parse_playlist_text,
)

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
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_cached_playlist_from_file(file_path: str) -> pd.DataFrame:
    return load_playlist(file_path)


@st.cache_data(show_spinner=False)
def get_cached_playlist_from_text(text: str) -> pd.DataFrame:
    return parse_playlist_text(text)


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


def render_network_html(graph: nx.Graph, height_px: int = 650) -> str:
    net = Network(
        height=f"{height_px}px",
        width="100%",
        bgcolor="#111827",
        font_color="#f9fafb",
    )

    degrees = dict(graph.degree())
    for node, data in graph.nodes(data=True):
        count = data.get("count", 1)
        deg = degrees.get(node, 1)
        node_size = max(10, min(42, int(count**0.5 * 3.5) + deg))
        node_color = "#ff4b4b" if count >= 20 else "#38bdf8"
        title = f"<b>{node}</b><br>Всего треков: {count}<br>Совместных связей: {deg}"
        net.add_node(
            node,
            label=node,
            size=node_size,
            title=title,
            color=node_color,
            borderWidth=1,
        )

    for u, v, data in graph.edges(data=True):
        weight = data.get("weight", 1)
        edge_title = f"Совместных треков: {weight}"
        edge_width = min(8, 1 + weight)
        net.add_edge(
            u,
            v,
            value=weight,
            width=edge_width,
            title=edge_title,
            color="#4b5563",
        )

    options_json = """{
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -60,
                "centralGravity": 0.015,
                "springLength": 90,
                "springStrength": 0.08,
                "damping": 0.88
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 100}
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 150,
            "navigationButtons": true
        }
    }"""
    net.set_options(options_json)
    return net.generate_html()


def main() -> None:
    st.sidebar.title("🎛️ Параметры плейлиста")

    uploaded_file = st.sidebar.file_uploader(
        "Загрузить файл плейлиста (.txt)",
        type=["txt"],
        help="Загрузите файл формата: <ID>. <Артист> - <Название> [<длительность>]",
    )

    if uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode("utf-8", errors="replace")
        df_raw = get_cached_playlist_from_text(file_content)
        source_name = uploaded_file.name
    elif os.path.exists(DEFAULT_FILE_PATH):
        df_raw = get_cached_playlist_from_file(DEFAULT_FILE_PATH)
        source_name = os.path.basename(DEFAULT_FILE_PATH)
    else:
        st.error(
            f"Файл по умолчанию не найден: {DEFAULT_FILE_PATH}. Пожалуйста, загрузите .txt файл через боковую панель."
        )
        st.stop()

    if df_raw.empty:
        st.warning("В файле не найдено корректных записей треков.")
        st.stop()

    chrono_mode = st.sidebar.radio(
        "Порядок треков по времени:",
        (
            "№1 = Самый недавний (стандарт VK)",
            "№1 = Самый первый (хронологический)",
        ),
        index=0,
    )

    if chrono_mode.startswith("№1 = Самый недавний"):
        df = df_raw.copy()
        df["time_order"] = len(df) - df["id"] + 1
    else:
        df = df_raw.copy()
        df["time_order"] = df["id"]

    dataset_fingerprint = f"{source_name}_{len(df)}"
    df["genre_cluster"] = get_cached_genres(df, dataset_fingerprint)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"📁 Источник: **{source_name}**")
    st.sidebar.caption(f"🎵 Всего треков: **{len(df):,}**")

    st.markdown('<div class="main-title">🎧 Анализ музыкального плейлиста</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-title">Глубокая интерактивная аналитика для <b>{len(df):,}</b> треков и вашей музыкальной истории</div>',
        unsafe_allow_html=True,
    )

    tab_overview, tab_genres, tab_timeline, tab_graph, tab_duration, tab_search = st.tabs(
        [
            "📊 Обзор (KPI)",
            "🎸 Жанры и плейлисты",
            "📈 Эволюция вкуса",
            "🕸️ Граф связей артистов",
            "⏱️ Хронометраж",
            "🔍 Каталог и поиск",
        ]
    )

    with tab_overview:
        all_artists_series = df.explode("all_artists")["all_artists"]
        unique_artists_count = all_artists_series.nunique()
        total_duration_sec = int(df["duration_sec"].sum())
        avg_duration_sec = int(df["duration_sec"].mean()) if len(df) > 0 else 0
        collab_tracks_count = int(df["is_collab"].sum())
        solo_tracks_count = len(df) - collab_tracks_count

        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{len(df):,}</div>
                    <div class="metric-label">Всего треков</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{unique_artists_count:,}</div>
                    <div class="metric-label">Уникальных артистов</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{format_seconds(total_duration_sec)}</div>
                    <div class="metric-label">Общее время звучания</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with kpi_col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{avg_duration_sec // 60}:{avg_duration_sec % 60:02d}</div>
                    <div class="metric-label">Средняя длительность</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("###")

        chart_col1, chart_col2 = st.columns([3, 2])
        with chart_col1:
            top_artists_df = (
                all_artists_series.value_counts()
                .head(20)
                .reset_index()
            )
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
            fig_top.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=20, r=20, t=40, b=20),
                height=520,
            )
            st.plotly_chart(fig_top, use_container_width=True)

        with chart_col2:
            fig_collab = px.pie(
                names=["Соло-треки", "Коллаборации / Фиты"],
                values=[solo_tracks_count, collab_tracks_count],
                title="Соотношение: Соло vs Фиты",
                hole=0.45,
                color_discrete_sequence=["#3b82f6", "#f97316"],
            )
            fig_collab.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                height=250,
            )
            st.plotly_chart(fig_collab, use_container_width=True)

            collab_artist_counts = (
                df[df["is_collab"]]
                .explode("all_artists")["all_artists"]
                .value_counts()
                .head(10)
                .reset_index()
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
            fig_collab_artists.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=20, r=20, t=40, b=20),
                height=250,
            )
            st.plotly_chart(fig_collab_artists, use_container_width=True)

    with tab_genres:
        st.markdown("### 🎸 Автоматическая кластеризация по жанрам")
        st.write(
            "Коллекция распределена по ключевым жанровым направлениям на основе тегов Last.fm, базы знаний и маркеров."
        )

        genre_counts = df["genre_cluster"].value_counts().reset_index()
        genre_counts.columns = ["Кластер", "Треков"]
        genre_counts["Процент"] = (genre_counts["Треков"] / len(df) * 100).round(1)

        g_col1, g_col2 = st.columns([3, 2])
        with g_col1:
            fig_genre_bar = px.bar(
                genre_counts,
                x="Кластер",
                y="Треков",
                color="Кластер",
                text="Треков",
                title="Распределение треков по жанровым направлениям",
                color_discrete_map={
                    CLUSTER_HEAVY_METAL: "#ef4444",
                    CLUSTER_DUBSTEP_EDM: "#06b6d4",
                    CLUSTER_PHONK_MEMPHIS: "#a855f7",
                    CLUSTER_HIPHOP_TRAP: "#f59e0b",
                    CLUSTER_ROCK_ALTERNATIVE: "#10b981",
                    CLUSTER_OTHER: "#6b7280",
                },
            )
            fig_genre_bar.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                height=380,
            )
            st.plotly_chart(fig_genre_bar, use_container_width=True)

        with g_col2:
            fig_genre_pie = px.pie(
                genre_counts,
                names="Кластер",
                values="Треков",
                hole=0.45,
                title="Доли направлений в коллекции",
                color="Кластер",
                color_discrete_map={
                    CLUSTER_HEAVY_METAL: "#ef4444",
                    CLUSTER_DUBSTEP_EDM: "#06b6d4",
                    CLUSTER_PHONK_MEMPHIS: "#a855f7",
                    CLUSTER_HIPHOP_TRAP: "#f59e0b",
                    CLUSTER_ROCK_ALTERNATIVE: "#10b981",
                    CLUSTER_OTHER: "#6b7280",
                },
            )
            fig_genre_pie.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                height=380,
            )
            st.plotly_chart(fig_genre_pie, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📥 Скачать готовые узкопрофильные плейлисты")

        cluster_keys = [
            (CLUSTER_HEAVY_METAL, "Плейлист_Heavy_Metal", "🎸"),
            (CLUSTER_DUBSTEP_EDM, "Плейлист_Dubstep_EDM", "🔊"),
            (CLUSTER_PHONK_MEMPHIS, "Плейлист_Phonk_Memphis", "💀"),
            (CLUSTER_HIPHOP_TRAP, "Плейлист_HipHop_Trap", "🎤"),
            (CLUSTER_ROCK_ALTERNATIVE, "Плейлист_Rock_Alternative", "⚡"),
            (CLUSTER_OTHER, "Плейлист_Other_Electronic", "🔀"),
        ]

        dl_cols = st.columns(len(cluster_keys))
        for i, (c_name, file_base, emoji) in enumerate(cluster_keys):
            c_tracks = df[df["genre_cluster"] == c_name]
            total_time = format_seconds(int(c_tracks["duration_sec"].sum()))
            with dl_cols[i]:
                st.markdown(f"**{emoji} {c_name}**")
                st.caption(f"{len(c_tracks):,} треков • {total_time}")

                txt_content = ""
                for idx_t, tr in enumerate(c_tracks.to_dict(orient="records"), 1):
                    txt_content += f"{idx_t}. {tr['artist_raw']} - {tr['title_raw']} [{tr['duration_fmt']}]\n"

                st.download_button(
                    label="📄 TXT",
                    data=txt_content,
                    file_name=f"{file_base}.txt",
                    mime="text/plain",
                    key=f"dl_txt_{c_name}",
                )

                m3u8_content = "#EXTM3U\n"
                for tr in c_tracks.to_dict(orient="records"):
                    m3u8_content += f"#EXTINF:{tr['duration_sec']},{tr['artist_raw']} - {tr['title_raw']}\n"
                    m3u8_content += f"{tr['artist_raw']} - {tr['title_raw']}.mp3\n"

                st.download_button(
                    label="🎶 M3U8",
                    data=m3u8_content,
                    file_name=f"{file_base}.m3u8",
                    mime="application/x-mpegURL",
                    key=f"dl_m3u8_{c_name}",
                )

        st.markdown("---")
        st.markdown("#### 🔍 Исследование треков конкретного жанра")
        selected_genre = st.selectbox(
            "Выберите жанр для просмотра артистов и списка композиций:",
            [k[0] for k in cluster_keys],
        )

        sub_df = df[df["genre_cluster"] == selected_genre]
        sub_top_artists = (
            sub_df.explode("all_artists")["all_artists"]
            .value_counts()
            .head(15)
            .reset_index()
        )
        sub_top_artists.columns = ["Артист", "Треков в жанре"]

        st.markdown(f"**Топ артистов в категории {selected_genre}:**")
        st.dataframe(sub_top_artists, use_container_width=True, hide_index=True)

        st.markdown(f"**Список треков ({len(sub_df):,}):**")
        st.dataframe(
            sub_df[["id", "artist_raw", "title_raw", "duration_fmt"]].rename(
                columns={
                    "id": "№",
                    "artist_raw": "Исполнитель",
                    "title_raw": "Название",
                    "duration_fmt": "Длительность",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with tab_timeline:
        st.markdown("### 📈 Изменение вкуса по хронологии добавления")
        st.write(
            "Анализ показывает, как с течением времени менялись ваши любимые исполнители и как трансформировался средний хронометраж песен."
        )

        time_controls_col1, time_controls_col2 = st.columns(2)
        with time_controls_col1:
            num_segments = st.slider(
                "Количество временных отрезков (сегментов):",
                min_value=4,
                max_value=16,
                value=8,
                step=1,
            )
        with time_controls_col2:
            top_n_timeline = st.slider(
                "Сколько ключевых артистов отслеживать:",
                min_value=4,
                max_value=12,
                value=7,
                step=1,
            )

        timeline_df = calculate_timeline_segments(
            df.sort_values("time_order"),
            num_segments=num_segments,
            top_n_artists=top_n_timeline,
        )

        fig_timeline = px.line(
            timeline_df,
            x="segment",
            y="count",
            color="artist",
            markers=True,
            title="Динамика количества треков топ-артистов по хронологическим эпохам",
            labels={"segment": "Временной интервал (диапазон треков)", "count": "Треков в периоде", "artist": "Артист"},
        )
        fig_timeline.update_layout(
            hovermode="x unified",
            margin=dict(l=20, r=20, t=40, b=20),
            height=430,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        st.markdown("---")
        st.markdown("#### ⏳ Тренд длительности: становились ли треки короче?")
        rolling_window = st.slider(
            "Размер скользящего окна сглаживания (треков):",
            min_value=50,
            max_value=500,
            value=200,
            step=50,
        )

        df_sorted_time = df.sort_values("time_order").copy()
        df_sorted_time["rolling_duration"] = (
            df_sorted_time["duration_sec"].rolling(window=rolling_window, min_periods=10).mean()
        )

        fig_duration_trend = px.line(
            df_sorted_time,
            x="time_order",
            y="rolling_duration",
            title=f"Скользящее среднее длительности треков (окно: {rolling_window} треков)",
            labels={"time_order": "Хронологический индекс трека", "rolling_duration": "Секунд"},
        )
        fig_duration_trend.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            height=380,
        )
        st.plotly_chart(fig_duration_trend, use_container_width=True)

        st.markdown("---")
        st.markdown("#### 🎯 Индивидуальный таймлайн конкретного артиста")
        popular_artists_list = all_artists_series.value_counts().head(200).index.tolist()
        selected_artist = st.selectbox(
            "Выберите исполнителя для просмотра его появления на шкале времени:",
            popular_artists_list,
        )

        if selected_artist:
            artist_mask = df["all_artists"].apply(lambda artists: selected_artist in artists)
            artist_tracks = df[artist_mask].copy()

            fig_artist_density = px.histogram(
                artist_tracks,
                x="time_order",
                nbins=40,
                title=f"Распределение добавления треков '{selected_artist}' (всего: {len(artist_tracks)})",
                labels={"time_order": "Порядковый номер в хронологии", "count": "Треков"},
                color_discrete_sequence=["#38bdf8"],
            )
            fig_artist_density.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                height=320,
            )
            st.plotly_chart(fig_artist_density, use_container_width=True)

    with tab_graph:
        st.markdown("### 🕸️ Интерактивный граф музыкальных коллабораций")
        st.write(
            "Узлы — музыканты, связи между ними — совместные композиции (фиты). "
            "Граф физически интерактивен: его можно перетаскивать, приближать колесом мыши и кликать по узлам."
        )

        graph_ctrl1, graph_ctrl2 = st.columns(2)
        with graph_ctrl1:
            min_collabs = st.slider(
                "Минимальное число совместных треков для отображения связи:",
                min_value=1,
                max_value=5,
                value=2,
                step=1,
                help="Увеличение порога фильтрует редкие случайные фиты, оставляя только устойчивые союзы.",
            )
        with graph_ctrl2:
            collab_artists_with_network = (
                df[df["is_collab"]].explode("all_artists")["all_artists"].value_counts()
            )
            focus_options = ["(Все артисты)"] + collab_artists_with_network.head(100).index.tolist()
            chosen_focus = st.selectbox(
                "Фокус на конкретном артисте (эго-сеть соавторов):",
                focus_options,
            )

        focus_arg = None if chosen_focus == "(Все артисты)" else chosen_focus
        network_graph = build_collaborations_graph(
            df,
            min_collaborations=min_collabs,
            focus_artist=focus_arg,
        )

        st.caption(
            f"Отображается: **{network_graph.number_of_nodes()}** артистов и **{network_graph.number_of_edges()}** совместных связей"
        )

        if network_graph.number_of_nodes() > 0:
            html_content = render_network_html(network_graph, height_px=650)
            st.components.v1.html(html_content, height=670, scrolling=False)
        else:
            st.info("По выбранным критериям не найдено связей. Попробуйте уменьшить порог фитов.")

        st.markdown("#### 🤝 Топ-10 самых частых совместных дуэтов")
        pair_counts = {}
        for _, row in df[df["is_collab"]].iterrows():
            arr = sorted(list(dict.fromkeys(row["all_artists"])))
            for i in range(len(arr)):
                for j in range(i + 1, len(arr)):
                    p = f"{arr[i]} & {arr[j]}"
                    pair_counts[p] = pair_counts.get(p, 0) + 1

        top_pairs_df = (
            pd.DataFrame(list(pair_counts.items()), columns=["Пара исполнителей", "Совместных треков"])
            .sort_values(by="Совместных треков", ascending=False)
            .head(10)
        )
        st.dataframe(top_pairs_df, use_container_width=True, hide_index=True)

    with tab_duration:
        st.markdown("### ⏱️ Анализ длительности треков")

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
            fig_hist.add_vline(
                x=mean_sec,
                line_dash="dash",
                line_color="#f59e0b",
                annotation_text=f"Среднее: {int(mean_sec//60)}:{int(mean_sec%60):02d}",
            )
            fig_hist.add_vline(
                x=median_sec,
                line_dash="dot",
                line_color="#ef4444",
                annotation_text=f"Медиана: {int(median_sec//60)}:{int(median_sec%60):02d}",
            )
            fig_hist.update_layout(
                margin=dict(l=20, r=20, t=40, b=20),
                height=420,
            )
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
            fig_box.update_layout(
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                height=420,
            )
            st.plotly_chart(fig_box, use_container_width=True)

        st.markdown("---")
        records_col1, records_col2 = st.columns(2)
        with records_col1:
            st.markdown("#### ⚡ Топ-15 самых коротких треков")
            short_df = (
                df.sort_values(by="duration_sec", ascending=True)
                .head(15)[["id", "artist_raw", "title_raw", "duration_fmt"]]
                .rename(
                    columns={
                        "id": "№",
                        "artist_raw": "Исполнитель",
                        "title_raw": "Трек",
                        "duration_fmt": "Время",
                    }
                )
            )
            st.dataframe(short_df, use_container_width=True, hide_index=True)

        with records_col2:
            st.markdown("#### ⏳ Топ-15 самых длинных треков")
            long_df = (
                df.sort_values(by="duration_sec", ascending=False)
                .head(15)[["id", "artist_raw", "title_raw", "duration_fmt"]]
                .rename(
                    columns={
                        "id": "№",
                        "artist_raw": "Исполнитель",
                        "title_raw": "Трек",
                        "duration_fmt": "Время",
                    }
                )
            )
            st.dataframe(long_df, use_container_width=True, hide_index=True)

    with tab_search:
        st.markdown("### 🔍 Поиск и фильтрация треков")

        search_query = st.text_input(
            "Поиск по артисту или названию песни:",
            placeholder="Введите, например: Ghostemane, Phonk, Remix, Sped up...",
        )

        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            genre_filter_choice = st.selectbox(
                "Фильтр по жанровому направлению:",
                ["Все жанры"] + [k[0] for k in cluster_keys],
            )
        with filter_col2:
            only_collabs = st.checkbox("Показывать только совместные треки (фиты)")
        with filter_col3:
            max_dur_limit = int(df["duration_sec"].max())
            selected_dur_range = st.slider(
                "Диапазон длительности (секунды):",
                min_value=0,
                max_value=max_dur_limit,
                value=(0, max_dur_limit),
                step=10,
            )

        filtered_df = df.copy()
        if search_query.strip():
            q = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df["artist_raw"].str.lower().str.contains(q)
                | filtered_df["title_raw"].str.lower().str.contains(q)
            ]

        if genre_filter_choice != "Все жанры":
            filtered_df = filtered_df[filtered_df["genre_cluster"] == genre_filter_choice]

        if only_collabs:
            filtered_df = filtered_df[filtered_df["is_collab"]]

        filtered_df = filtered_df[
            (filtered_df["duration_sec"] >= selected_dur_range[0])
            & (filtered_df["duration_sec"] <= selected_dur_range[1])
        ]

        st.caption(f"Найдено треков: **{len(filtered_df):,}** из {len(df):,}")

        display_columns = ["id", "artist_raw", "title_raw", "genre_cluster", "duration_fmt", "is_collab"]
        display_df = filtered_df[display_columns].rename(
            columns={
                "id": "№",
                "artist_raw": "Исполнитель",
                "title_raw": "Название",
                "genre_cluster": "Жанр",
                "duration_fmt": "Длительность",
                "is_collab": "Фит?",
            }
        )
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_data = display_df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 Скачать найденные треки в CSV",
            data=csv_data,
            file_name="filtered_music_tracks.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
