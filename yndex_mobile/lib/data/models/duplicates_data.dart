class DuplicateTrackItem {
  final String id;
  final String title;
  final String artist;
  final List<String> allArtists;
  final int durationSec;
  final String durationFmt;
  final String genreCluster;
  final String? coverUrl;
  final String? yandexUrl;
  final bool isOriginal;

  const DuplicateTrackItem({
    required this.id,
    required this.title,
    required this.artist,
    required this.allArtists,
    required this.durationSec,
    required this.durationFmt,
    required this.genreCluster,
    this.coverUrl,
    this.yandexUrl,
    required this.isOriginal,
  });

  factory DuplicateTrackItem.fromJson(Map<String, dynamic> json) {
    return DuplicateTrackItem(
      id: json['id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      artist: json['artist']?.toString() ?? '',
      allArtists: (json['all_artists'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      durationSec: (json['duration_sec'] as num?)?.toInt() ?? 0,
      durationFmt: json['duration_fmt']?.toString() ?? '0:00',
      genreCluster: json['genre_cluster']?.toString() ?? 'Other & Electronic',
      coverUrl: json['cover_url']?.toString(),
      yandexUrl: json['yandex_url']?.toString(),
      isOriginal: json['is_original'] == true,
    );
  }
}

class DuplicateGroup {
  final String key;
  final String artist;
  final String title;
  final int count;
  final List<DuplicateTrackItem> tracks;

  const DuplicateGroup({
    required this.key,
    required this.artist,
    required this.title,
    required this.count,
    required this.tracks,
  });

  factory DuplicateGroup.fromJson(Map<String, dynamic> json) {
    return DuplicateGroup(
      key: json['key']?.toString() ?? '',
      artist: json['artist']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      count: (json['count'] as num?)?.toInt() ?? 0,
      tracks: (json['tracks'] as List<dynamic>?)
              ?.map((t) => DuplicateTrackItem.fromJson(t as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class DuplicatesData {
  final bool success;
  final int totalDuplicates;
  final int duplicateGroupsCount;
  final int totalRedundantTimeSec;
  final String totalRedundantTimeFmt;
  final List<DuplicateGroup> groups;

  const DuplicatesData({
    required this.success,
    required this.totalDuplicates,
    required this.duplicateGroupsCount,
    required this.totalRedundantTimeSec,
    required this.totalRedundantTimeFmt,
    required this.groups,
  });

  factory DuplicatesData.fromJson(Map<String, dynamic> json) {
    return DuplicatesData(
      success: json['success'] == true,
      totalDuplicates: (json['total_duplicates'] as num?)?.toInt() ?? 0,
      duplicateGroupsCount: (json['duplicate_groups_count'] as num?)?.toInt() ?? 0,
      totalRedundantTimeSec: (json['total_redundant_time_sec'] as num?)?.toInt() ?? 0,
      totalRedundantTimeFmt: json['total_redundant_time_fmt']?.toString() ?? '0:00',
      groups: (json['groups'] as List<dynamic>?)
              ?.map((g) => DuplicateGroup.fromJson(g as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
