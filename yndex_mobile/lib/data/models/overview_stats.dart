class TopArtist {
  final String artist;
  final int count;

  TopArtist({required this.artist, required this.count});

  factory TopArtist.fromJson(Map<String, dynamic> json) {
    return TopArtist(
      artist: json['artist'] as String? ?? 'Unknown',
      count: (json['count'] as num?)?.toInt() ?? 0,
    );
  }
}

class OverviewStats {
  final int totalTracks;
  final int totalDurationSec;
  final String totalDurationFmt;
  final int avgDurationSec;
  final String avgDurationFmt;
  final int uniqueArtists;
  final int soloCount;
  final int collabCount;
  final double collabRatioPercent;
  final List<TopArtist> topArtists;

  OverviewStats({
    required this.totalTracks,
    required this.totalDurationSec,
    required this.totalDurationFmt,
    required this.avgDurationSec,
    required this.avgDurationFmt,
    required this.uniqueArtists,
    required this.soloCount,
    required this.collabCount,
    required this.collabRatioPercent,
    required this.topArtists,
  });

  factory OverviewStats.fromJson(Map<String, dynamic> json) {
    final rawArtists = json['top_artists'] as List<dynamic>? ?? [];
    return OverviewStats(
      totalTracks: (json['total_tracks'] as num?)?.toInt() ?? 0,
      totalDurationSec: (json['total_duration_sec'] as num?)?.toInt() ?? 0,
      totalDurationFmt: json['total_duration_fmt'] as String? ?? '0 мин.',
      avgDurationSec: (json['avg_duration_sec'] as num?)?.toInt() ?? 0,
      avgDurationFmt: json['avg_duration_fmt'] as String? ?? '0:00',
      uniqueArtists: (json['unique_artists'] as num?)?.toInt() ?? 0,
      soloCount: (json['solo_count'] as num?)?.toInt() ?? 0,
      collabCount: (json['collab_count'] as num?)?.toInt() ?? 0,
      collabRatioPercent: (json['collab_ratio_percent'] as num?)?.toDouble() ?? 0.0,
      topArtists: rawArtists.map((e) => TopArtist.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
