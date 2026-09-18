import 'package:flutter_test/flutter_test.dart';
import 'package:yndex_mobile/data/models/genre_cluster.dart';
import 'package:yndex_mobile/data/models/overview_stats.dart';
import 'package:yndex_mobile/core/utils/formatters.dart';

void main() {
  group('Music Analytics Models & Formatters Test', () {
    test('Formatters test', () {
      expect(Formatters.formatSecondsToMinutes(192), '3:12');
      expect(Formatters.formatDurationDetailed(3665), '1 ч. 1 мин.');
    });

    test('GenreCluster model fromJson test', () {
      final json = {
        'name': 'Dubstep & EDM',
        'count': 2295,
        'percent': 25.6,
        'color': '#00E5FF',
        'icon': 'electric_bolt',
      };
      final cluster = GenreCluster.fromJson(json);
      expect(cluster.name, 'Dubstep & EDM');
      expect(cluster.count, 2295);
      expect(cluster.percent, 25.6);
    });

    test('OverviewStats model fromJson test', () {
      final json = {
        'total_tracks': 8965,
        'total_duration_sec': 1720000,
        'total_duration_fmt': '19 дн. 22 ч. 10 мин.',
        'avg_duration_sec': 192,
        'avg_duration_fmt': '3:12',
        'unique_artists': 1420,
        'solo_count': 5799,
        'collab_count': 3166,
        'collab_ratio_percent': 35.3,
        'top_artists': [
          {'artist': 'Skrillex', 'count': 120}
        ],
      };
      final stats = OverviewStats.fromJson(json);
      expect(stats.totalTracks, 8965);
      expect(stats.topArtists.first.artist, 'Skrillex');
      expect(stats.topArtists.first.count, 120);
    });
  });
}
