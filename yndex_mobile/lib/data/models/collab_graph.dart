import 'package:flutter/material.dart';

class GraphNode {
  final String id;
  final String name;
  final int tracksCount;
  final int degree;
  final String dominantGenre;
  final Color color;
  final double x;
  final double y;

  GraphNode({
    required this.id,
    required this.name,
    required this.tracksCount,
    required this.degree,
    required this.dominantGenre,
    required this.color,
    required this.x,
    required this.y,
  });

  factory GraphNode.fromJson(Map<String, dynamic> json) {
    final colorHex = json['color'] as String? ?? '#00E5FF';
    final parsedColor = _parseHexColor(colorHex);

    return GraphNode(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      tracksCount: (json['tracks_count'] as num?)?.toInt() ?? 1,
      degree: (json['degree'] as num?)?.toInt() ?? 0,
      dominantGenre: json['dominant_genre'] as String? ?? 'Other',
      color: parsedColor,
      x: (json['x'] as num?)?.toDouble() ?? 0.0,
      y: (json['y'] as num?)?.toDouble() ?? 0.0,
    );
  }

  static Color _parseHexColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '').trim();
      if (clean.length == 6) {
        return Color(int.parse('FF$clean', radix: 16));
      }
      return const Color(0xFF00E5FF);
    } catch (_) {
      return const Color(0xFF00E5FF);
    }
  }
}

class GraphEdge {
  final String source;
  final String target;
  final int weight;

  GraphEdge({
    required this.source,
    required this.target,
    required this.weight,
  });

  factory GraphEdge.fromJson(Map<String, dynamic> json) {
    return GraphEdge(
      source: json['source'] as String? ?? '',
      target: json['target'] as String? ?? '',
      weight: (json['weight'] as num?)?.toInt() ?? 1,
    );
  }
}

class CollabGraphData {
  final List<GraphNode> nodes;
  final List<GraphEdge> edges;
  final int totalNodes;
  final int totalEdges;
  final String? focusArtist;

  CollabGraphData({
    required this.nodes,
    required this.edges,
    required this.totalNodes,
    required this.totalEdges,
    this.focusArtist,
  });

  factory CollabGraphData.fromJson(Map<String, dynamic> json) {
    final rawNodes = json['nodes'] as List<dynamic>? ?? [];
    final rawEdges = json['edges'] as List<dynamic>? ?? [];
    final stats = json['stats'] as Map<String, dynamic>? ?? {};

    return CollabGraphData(
      nodes: rawNodes
          .map((e) => GraphNode.fromJson(e as Map<String, dynamic>))
          .toList(),
      edges: rawEdges
          .map((e) => GraphEdge.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalNodes: (stats['total_nodes'] as num?)?.toInt() ?? rawNodes.length,
      totalEdges: (stats['total_edges'] as num?)?.toInt() ?? rawEdges.length,
      focusArtist: stats['focus_artist'] as String?,
    );
  }
}
