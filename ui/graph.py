from itertools import combinations
import json
import networkx as nx
import pandas as pd
import streamlit as st

from parser import build_collaborations_graph


def render_network_html(graph: nx.Graph, height_px: int = 650) -> str:
    """Генерирует HTML представление интерактивного графа Vis.js без библиотеки pyvis."""
    degrees = dict(graph.degree())
    nodes = []
    for node, data in graph.nodes(data=True):
        count = data.get("count", 1)
        deg = degrees.get(node, 1)
        node_size = max(12, min(42, int(count**0.5 * 3.5) + deg))
        node_color = "#ff4b4b" if count >= 20 else "#38bdf8"
        nodes.append({
            "id": node,
            "label": node,
            "value": count,
            "size": node_size,
            "color": {"background": node_color, "border": "#ffffff", "highlight": {"background": "#ffffff", "border": node_color}},
            "title": f"<b>{node}</b><br>Всего треков: {count}<br>Совместных связей: {deg}",
            "font": {"color": "#f9fafb", "size": 13, "face": "Inter, sans-serif"},
        })

    edges = []
    for u, v, data in graph.edges(data=True):
        weight = data.get("weight", 1)
        edges.append({
            "from": u,
            "to": v,
            "value": weight,
            "width": min(8, 1 + weight),
            "title": f"Совместных треков: {weight}",
            "color": {"color": "rgba(75, 85, 99, 0.7)", "highlight": "#38bdf8"},
        })

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background-color: #111827; overflow: hidden; }}
#vis_container {{ width: 100%; height: {height_px}px; }}
</style></head><body>
<div id="vis_container"></div>
<script type="text/javascript">
const data = {{ nodes: new vis.DataSet({nodes_json}), edges: new vis.DataSet({edges_json}) }};
const options = {{
  nodes: {{ shape: 'dot', borderWidth: 1 }},
  physics: {{
    forceAtlas2Based: {{ gravitationalConstant: -60, centralGravity: 0.015, springLength: 90, springStrength: 0.08, damping: 0.88 }},
    solver: 'forceAtlas2Based',
    stabilization: {{ iterations: 100 }}
  }},
  interaction: {{ hover: true, tooltipDelay: 150, navigationButtons: true, zoomView: true, dragView: true }}
}};
new vis.Network(document.getElementById('vis_container'), data, options);
</script></body></html>"""


def _render_top_duets(df: pd.DataFrame) -> None:
    st.markdown("#### 🤝 Топ-10 самых частых совместных дуэтов")
    pair_counts = {}
    for _, row in df[df["is_collab"]].iterrows():
        arr = sorted(list(dict.fromkeys(row["all_artists"])))
        for a1, a2 in combinations(arr, 2):
            p = f"{a1} & {a2}"
            pair_counts[p] = pair_counts.get(p, 0) + 1

    top_pairs_df = (
        pd.DataFrame(list(pair_counts.items()), columns=["Пара исполнителей", "Совместных треков"])
        .sort_values(by="Совместных треков", ascending=False)
        .head(10)
    )
    st.dataframe(top_pairs_df, use_container_width=True, hide_index=True)


def render_graph_tab(df: pd.DataFrame) -> None:
    """Отображает вкладку графа коллабораций артистов."""
    st.markdown("### 🕸️ Интерактивный граф музыкальных коллабораций")
    st.write("Узлы — музыканты, связи между ними — совместные композиции (фиты).")

    graph_ctrl1, graph_ctrl2 = st.columns(2)
    with graph_ctrl1:
        min_collabs = st.slider("Минимальное число совместных треков:", 1, 5, 2, 1)
    with graph_ctrl2:
        collab_artists = df[df["is_collab"]].explode("all_artists")["all_artists"].value_counts()
        focus_options = ["(Все артисты)"] + collab_artists.head(100).index.tolist()
        chosen_focus = st.selectbox("Фокус на конкретном артисте:", focus_options)

    focus_arg = None if chosen_focus == "(Все артисты)" else chosen_focus
    network_graph = build_collaborations_graph(df, min_collaborations=min_collabs, focus_artist=focus_arg)
    st.caption(f"Отображается: **{network_graph.number_of_nodes()}** артистов и **{network_graph.number_of_edges()}** связей")

    if network_graph.number_of_nodes() > 0:
        html_content = render_network_html(network_graph, height_px=650)
        st.components.v1.html(html_content, height=670, scrolling=False)
        st.download_button(
            label="🌐 Скачать граф как автономный HTML",
            data=html_content,
            file_name="collaborations_graph.html",
            mime="text/html",
            help="Скачать интерактивный 3D-граф со связями в виде отдельного веб-файла",
        )
    else:
        st.info("По выбранным критериям не найдено связей.")

    _render_top_duets(df)
