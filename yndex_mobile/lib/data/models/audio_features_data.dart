class BpmProfileItem {
  final String range;
  final String label;
  final int count;
  final double percent;
  final String color;

  const BpmProfileItem({
    required this.range,
    required this.label,
    required this.count,
    required this.percent,
    required this.color,
  });

  factory BpmProfileItem.fromJson(Map<String, dynamic> json) {
    return BpmProfileItem(
      range: json['range']?.toString() ?? '',
      label: json['label']?.toString() ?? '',
      count: (json['count'] as num?)?.toInt() ?? 0,
      percent: (json['percent'] as num?)?.toDouble() ?? 0.0,
      color: json['color']?.toString() ?? '#00E5FF',
    );
  }
}

class LoudnessProfile {
  final double heavyLufsPercent;
  final double standardLufsPercent;
  final double acousticLufsPercent;

  const LoudnessProfile({
    required this.heavyLufsPercent,
    required this.standardLufsPercent,
    required this.acousticLufsPercent,
  });

  factory LoudnessProfile.fromJson(Map<String, dynamic> json) {
    return LoudnessProfile(
      heavyLufsPercent: (json['heavy_lufs_percent'] as num?)?.toDouble() ?? 0.0,
      standardLufsPercent: (json['standard_lufs_percent'] as num?)?.toDouble() ?? 0.0,
      acousticLufsPercent: (json['acoustic_lufs_percent'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class AudioFeaturesData {
  final bool success;
  final int totalTracks;
  final double energyScorePercent;
  final String energyLabel;
  final int averageDurationSec;
  final String averageDurationFmt;
  final double collabRatioPercent;
  final List<BpmProfileItem> bpmProfile;
  final LoudnessProfile loudnessProfile;

  const AudioFeaturesData({
    required this.success,
    required this.totalTracks,
    required this.energyScorePercent,
    required this.energyLabel,
    required this.averageDurationSec,
    required this.averageDurationFmt,
    required this.collabRatioPercent,
    required this.bpmProfile,
    required this.loudnessProfile,
  });

  factory AudioFeaturesData.fromJson(Map<String, dynamic> json) {
    return AudioFeaturesData(
      success: json['success'] == true,
      totalTracks: (json['total_tracks'] as num?)?.toInt() ?? 0,
      energyScorePercent: (json['energy_score_percent'] as num?)?.toDouble() ?? 0.0,
      energyLabel: json['energy_label']?.toString() ?? 'Сбалансированная',
      averageDurationSec: (json['average_duration_sec'] as num?)?.toInt() ?? 0,
      averageDurationFmt: json['average_duration_fmt']?.toString() ?? '0:00',
      collabRatioPercent: (json['collab_ratio_percent'] as num?)?.toDouble() ?? 0.0,
      bpmProfile: (json['bpm_profile'] as List<dynamic>?)
              ?.map((item) => BpmProfileItem.fromJson(item as Map<String, dynamic>))
              .toList() ??
          [],
      loudnessProfile: json['loudness_profile'] != null
          ? LoudnessProfile.fromJson(json['loudness_profile'] as Map<String, dynamic>)
          : const LoudnessProfile(heavyLufsPercent: 0, standardLufsPercent: 0, acousticLufsPercent: 0),
    );
  }
}
