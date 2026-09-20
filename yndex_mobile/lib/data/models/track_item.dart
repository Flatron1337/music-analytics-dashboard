import 'package:flutter/material.dart';

class TrackItem {
  final int id;
  final String title;
  final String artist;
  final List<String> artists;
  final int durationSec;
  final String durationFmt;
  final String genre;
  final String genreColorHex;
  final bool isCollab;
  final String coverUri;
  final String yandexUrl;

  TrackItem({
    required this.id,
    required this.title,
    required this.artist,
    required this.artists,
    required this.durationSec,
    required this.durationFmt,
    required this.genre,
    required this.genreColorHex,
    required this.isCollab,
    required this.coverUri,
    required this.yandexUrl,
  });

  Color get genreColor {
    try {
      final clean = genreColorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.amber;
    }
  }

  factory TrackItem.fromJson(Map<String, dynamic> json) {
    final rawArtists = json['artists'] as List<dynamic>? ?? [];
    return TrackItem(
      id: (json['id'] as num?)?.toInt() ?? 0,
      title: json['title'] as String? ?? 'Unknown Title',
      artist: json['artist'] as String? ?? 'Unknown Artist',
      artists: rawArtists.map((e) => e.toString()).toList(),
      durationSec: (json['duration_sec'] as num?)?.toInt() ?? 0,
      durationFmt: json['duration_fmt'] as String? ?? '0:00',
      genre: json['genre'] as String? ?? 'Other',
      genreColorHex: json['genre_color'] as String? ?? '#FFCC00',
      isCollab: json['is_collab'] as bool? ?? false,
      coverUri: json['cover_uri'] as String? ?? '',
      yandexUrl: json['yandex_url'] as String? ?? '',
    );
  }
}
