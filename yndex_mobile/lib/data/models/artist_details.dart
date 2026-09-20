import 'package:flutter/material.dart';
import 'track_item.dart';

class ArtistGenreShare {
  final String genre;
  final int count;
  final double percent;
  final String colorHex;

  ArtistGenreShare({
    required this.genre,
    required this.count,
    required this.percent,
    required this.colorHex,
  });

  Color get color {
    try {
      final clean = colorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.amber;
    }
  }

  factory ArtistGenreShare.fromJson(Map<String, dynamic> json) {
    return ArtistGenreShare(
      genre: json['genre'] as String? ?? 'Other',
      count: (json['count'] as num?)?.toInt() ?? 0,
      percent: (json['percent'] as num?)?.toDouble() ?? 0.0,
      colorHex: json['color'] as String? ?? '#FFCC00',
    );
  }
}

class ArtistCollaborator {
  final String artist;
  final int count;

  ArtistCollaborator({required this.artist, required this.count});

  factory ArtistCollaborator.fromJson(Map<String, dynamic> json) {
    return ArtistCollaborator(
      artist: json['artist'] as String? ?? 'Unknown',
      count: (json['count'] as num?)?.toInt() ?? 0,
    );
  }
}

class ArtistDetails {
  final String artist;
  final int? rank;
  final int totalTracks;
  final double librarySharePercent;
  final int totalDurationSec;
  final String totalDurationFmt;
  final int avgDurationSec;
  final int soloCount;
  final int collabCount;
  final String dominantGenre;
  final String dominantColorHex;
  final List<ArtistGenreShare> genres;
  final List<ArtistCollaborator> topCollaborators;
  final List<TrackItem> tracks;
  final String yandexUrl;

  ArtistDetails({
    required this.artist,
    this.rank,
    required this.totalTracks,
    required this.librarySharePercent,
    required this.totalDurationSec,
    required this.totalDurationFmt,
    required this.avgDurationSec,
    required this.soloCount,
    required this.collabCount,
    required this.dominantGenre,
    required this.dominantColorHex,
    required this.genres,
    required this.topCollaborators,
    required this.tracks,
    required this.yandexUrl,
  });

  Color get dominantColor {
    try {
      final clean = dominantColorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.amber;
    }
  }

  factory ArtistDetails.fromJson(Map<String, dynamic> json) {
    final rawGenres = json['genres'] as List<dynamic>? ?? [];
    final rawCollabs = json['top_collaborators'] as List<dynamic>? ?? [];
    final rawTracks = json['tracks'] as List<dynamic>? ?? [];

    return ArtistDetails(
      artist: json['artist'] as String? ?? 'Артист',
      rank: (json['rank'] as num?)?.toInt(),
      totalTracks: (json['total_tracks'] as num?)?.toInt() ?? 0,
      librarySharePercent: (json['library_share_percent'] as num?)?.toDouble() ?? 0.0,
      totalDurationSec: (json['total_duration_sec'] as num?)?.toInt() ?? 0,
      totalDurationFmt: json['total_duration_fmt'] as String? ?? '0:00',
      avgDurationSec: (json['avg_duration_sec'] as num?)?.toInt() ?? 0,
      soloCount: (json['solo_count'] as num?)?.toInt() ?? 0,
      collabCount: (json['collab_count'] as num?)?.toInt() ?? 0,
      dominantGenre: json['dominant_genre'] as String? ?? 'Unknown',
      dominantColorHex: json['dominant_color'] as String? ?? '#FFCC00',
      genres: rawGenres.map((e) => ArtistGenreShare.fromJson(e as Map<String, dynamic>)).toList(),
      topCollaborators: rawCollabs.map((e) => ArtistCollaborator.fromJson(e as Map<String, dynamic>)).toList(),
      tracks: rawTracks.map((e) => TrackItem.fromJson(e as Map<String, dynamic>)).toList(),
      yandexUrl: json['yandex_url'] as String? ?? '',
    );
  }
}
