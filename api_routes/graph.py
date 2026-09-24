import json
from typing import Any, Dict, List, Optional, Tuple
from flask import Blueprint, jsonify, request, Response
import networkx as nx
import pandas as pd

from api_routes.state import (
    CLUSTER_COLORS,
    CLUSTER_OTHER,
    get_dataset,
)
from parser import build_collaborations_graph

graph_bp = Blueprint("graph", __name__)


def _filter_subgraph(full_graph: nx.Graph, focus_artist: Optional[str], limit_nodes: int) -> nx.Graph:
    if not focus_artist and full_graph.number_of_nodes() > limit_nodes:
        top_candidates = sorted(
            full_graph.nodes(),
            key=lambda n: (full_graph.degree(n), full_graph.nodes[n].get("count", 0)),
            reverse=True,
        )[:limit_nodes]
        subg = full_graph.subgraph(top_candidates).copy()
        connected = [n for n in subg.nodes() if subg.degree(n) > 0]
        return subg.subgraph(connected).copy() if connected else subg
    return full_graph


def _extract_artist_genres(df: pd.DataFrame, graph: nx.Graph) -> Dict[str, str]:
    artist_genres: Dict[str, str] = {}
    if "is_collab" in df.columns and "all_artists" in df.columns:
        collab_subset = df[df["is_collab"]]
        if not collab_subset.empty:
            exploded = collab_subset.explode("all_artists")
            grouped = exploded.groupby(["all_artists", "genre_cluster"]).size().unstack(fill_value=0)
            for art in graph.nodes():
                if art in grouped.index:
                    artist_genres[art] = grouped.loc[art].idxmax()
    return artist_genres


def _serialize_graph_elements(
    graph: nx.Graph,
    pos: Dict[Any, Any],
    artist_genres: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    degrees = dict(graph.degree())
    nodes_list = []
    for node, data in graph.nodes(data=True):
        count = int(data.get("count", 1))
        deg = int(degrees.get(node, 0))
        coords = pos.get(node, [0.0, 0.0])
        dom_genre = artist_genres.get(node, CLUSTER_OTHER)
        nodes_list.append({
            "id": node,
            "name": node,
            "tracks_count": count,
            "degree": deg,
            "dominant_genre": dom_genre,
            "color": CLUSTER_COLORS.get(dom_genre, "#00E5FF"),
            "x": round(float(coords[0]), 4),
            "y": round(float(coords[1]), 4),
        })

    edges_list = [
        {"source": u, "target": v, "weight": int(data.get("weight", 1))}
        for u, v, data in graph.edges(data=True)
    ]
    nodes_list.sort(key=lambda n: n["tracks_count"], reverse=True)
    return nodes_list, edges_list


@graph_bp.route("/api/collaborations-graph", methods=["GET"])
def get_collaborations_graph():
    df = get_dataset()
    if df.empty:
        return jsonify({"nodes": [], "edges": [], "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": None}})

    min_collabs = max(1, int(request.args.get("min_collabs", 1)))
    limit_nodes = max(10, int(request.args.get("limit_nodes", 60)))
    focus = request.args.get("focus_artist", "").strip() or None

    full_graph = build_collaborations_graph(df, min_collaborations=min_collabs, focus_artist=focus)
    if full_graph.number_of_nodes() == 0:
        return jsonify({"nodes": [], "edges": [], "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": focus}})

    graph = _filter_subgraph(full_graph, focus, limit_nodes)
    if graph.number_of_nodes() == 0:
        return jsonify({"nodes": [], "edges": [], "stats": {"total_nodes": 0, "total_edges": 0, "focus_artist": focus}})

    pos = nx.spring_layout(graph, k=0.45, iterations=50, seed=42)
    artist_genres = _extract_artist_genres(df, graph)
    nodes_list, edges_list = _serialize_graph_elements(graph, pos, artist_genres)

    return jsonify({
        "nodes": nodes_list,
        "edges": edges_list,
        "stats": {
            "total_nodes": len(nodes_list),
            "total_edges": len(edges_list),
            "min_collaborations": min_collabs,
            "focus_artist": focus,
        },
    })


def _build_vis_elements(graph: nx.Graph, artist_genres: Dict[str, str]) -> Tuple[str, str, int, int]:
    vis_nodes = []
    for node, data in graph.nodes(data=True):
        count = int(data.get("count", 1))
        deg = int(graph.degree(node))
        dom_genre = artist_genres.get(node, CLUSTER_OTHER)
        color = CLUSTER_COLORS.get(dom_genre, "#00E5FF")
        vis_nodes.append({
            "id": node,
            "label": node,
            "value": count,
            "title": f"<b>{node}</b><br>Жанр: {dom_genre}<br>Треков: {count}<br>Фитов: {deg}",
            "color": {"background": color, "border": "#ffffff", "highlight": {"background": "#ffffff", "border": color}},
            "font": {"color": "#ffffff", "face": "Inter, sans-serif", "size": 14},
        })

    vis_edges = [
        {
            "from": u,
            "to": v,
            "value": int(data.get("weight", 1)),
            "title": f"Совместных треков: {int(data.get('weight', 1))}",
            "color": {"color": "rgba(255, 255, 255, 0.25)", "highlight": "#00E5FF"},
        }
        for u, v, data in graph.edges(data=True)
    ]
    return (
        json.dumps(vis_nodes, ensure_ascii=False),
        json.dumps(vis_edges, ensure_ascii=False),
        len(vis_nodes),
        len(vis_edges),
    )


def _render_vis_html(nodes_json: str, edges_json: str, n_cnt: int, e_cnt: int) -> str:
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>Карта коллабораций артистов</title>
<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0B0E14; color:#F0F4F8; font-family:'Inter',sans-serif; overflow:hidden; width:100vw; height:100vh; }}
#header {{ position:absolute; top:16px; left:20px; z-index:10; background:rgba(18,24,38,0.85); backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,0.1); border-radius:16px; padding:16px 24px; }}
h1 {{ font-size:20px; font-weight:800; background:linear-gradient(135deg, #00E5FF, #D500F9); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
#legend {{ position:absolute; bottom:20px; left:20px; z-index:10; background:rgba(18,24,38,0.85); backdrop-filter:blur(12px); border-radius:16px; padding:14px 20px; display:flex; gap:16px; flex-wrap:wrap; }}
.legend-dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
#network {{ width:100vw; height:100vh; }}
</style></head><body>
<div id="header"><h1>🕸️ Карта коллабораций артистов</h1><p style="font-size:13px;color:#94A3B8;">Узлов: {n_cnt} • Связей: {e_cnt}</p></div>
<div id="network"></div>
<script>
const container = document.getElementById('network');
const data = {{ nodes: new vis.DataSet({nodes_json}), edges: new vis.DataSet({edges_json}) }};
const options = {{
  nodes: {{ shape: 'dot', scaling: {{ min: 14, max: 40 }}, borderWidth: 2 }},
  edges: {{ smooth: {{ type: 'continuous' }}, scaling: {{ min: 1.5, max: 8 }} }},
  physics: {{ stabilization: true, barnesHut: {{ gravitationalConstant: -18000, springConstant: 0.04, springLength: 95 }} }},
  interaction: {{ hover: true, tooltipDelay: 100, zoomView: true, dragView: true }}
}};
new vis.Network(container, data, options);
</script></body></html>"""


@graph_bp.route("/api/collaborations-graph/export-html", methods=["GET"])
def export_collaborations_graph_html():
    df = get_dataset()
    if df.empty or "is_collab" not in df.columns:
        return "<h3>Нет данных для построения графа</h3>", 400

    min_collabs = int(request.args.get("min_collabs", 1))
    limit_nodes = int(request.args.get("limit_nodes", 75))

    full_graph = build_collaborations_graph(df, min_collaborations=min_collabs)
    if full_graph.number_of_nodes() == 0:
        return "<h3>Граф пуст при данных фильтрах</h3>", 400

    graph = _filter_subgraph(full_graph, None, limit_nodes)
    artist_genres = _extract_artist_genres(df, graph)
    nodes_json, edges_json, n_cnt, e_cnt = _build_vis_elements(graph, artist_genres)
    html_content = _render_vis_html(nodes_json, edges_json, n_cnt, e_cnt)

    return Response(
        html_content,
        mimetype="text/html",
        headers={"Content-Disposition": "attachment; filename=collaborations_graph.html"},
    )
