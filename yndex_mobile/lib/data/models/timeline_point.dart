import 'package:flutter/material.dart';

class TimelineGenreShare {
  final String genre;
  final int count;
  final String colorHex;
  final double percent;

  TimelineGenreShare({
    required this.genre,
    required this.count,
    required this.colorHex,
    required this.percent,
  });

  Color get color {
    try {
      final clean = colorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.grey;
    }
  }

  factory TimelineGenreShare.fromJson(Map<String, dynamic> json) {
    return TimelineGenreShare(
      genre: json['genre'] as String? ?? 'Other',
      count: (json['count'] as num?)?.toInt() ?? 0,
      colorHex: json['color'] as String? ?? '#999999',
      percent: (json['percent'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class TimelineSegment {
  final int segmentIndex;
  final String label;
  final int tracksCount;
  final String dominantGenre;
  final String dominantColorHex;
  final List<TimelineGenreShare> genres;

  TimelineSegment({
    required this.segmentIndex,
    required this.label,
    required this.tracksCount,
    required this.dominantGenre,
    required this.dominantColorHex,
    required this.genres,
  });

  Color get dominantColor {
    try {
      final clean = dominantColorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.amber;
    }
  }

  factory TimelineSegment.fromJson(Map<String, dynamic> json) {
    final rawGenres = json['genres'] as List<dynamic>? ?? [];
    return TimelineSegment(
      segmentIndex: (json['segment_index'] as num?)?.toInt() ?? 0,
      label: json['label'] as String? ?? '',
      tracksCount: (json['tracks_count'] as num?)?.toInt() ?? 0,
      dominantGenre: json['dominant_genre'] as String? ?? 'Unknown',
      dominantColorHex: json['dominant_color'] as String? ?? '#FFCC00',
      genres: rawGenres.map((e) => TimelineGenreShare.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
