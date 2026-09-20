import 'package:flutter_test/flutter_test.dart';
import 'package:yndex_mobile/data/models/genre_cluster.dart';
import 'package:yndex_mobile/data/models/overview_stats.dart';
import 'package:yndex_mobile/data/models/track_item.dart';
import 'package:yndex_mobile/data/models/timeline_point.dart';
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

    test('TrackItem model fromJson test with coverUri', () {
      final json = {
        'id': 42,
        'title': 'Scary Monsters and Nice Sprites',
        'artist': 'Skrillex',
        'artists': ['Skrillex'],
        'duration_sec': 243,
        'duration_fmt': '4:03',
        'genre': 'Dubstep & EDM',
        'genre_color': '#00E5FF',
        'is_collab': false,
        'cover_uri': 'https://avatars.yandex.net/get-music-content/123/456/200x200',
        'yandex_url': 'https://music.yandex.ru/track/42',
      };
      final track = TrackItem.fromJson(json);
      expect(track.id, 42);
      expect(track.title, 'Scary Monsters and Nice Sprites');
      expect(track.artist, 'Skrillex');
      expect(track.coverUri, 'https://avatars.yandex.net/get-music-content/123/456/200x200');
      expect(track.isCollab, false);
    });

    test('TimelineSegment model fromJson test', () {
      final json = {
        'segment_index': 0,
        'label': '#1–#1000',
        'tracks_count': 1000,
        'dominant_genre': 'Dubstep & EDM',
        'dominant_color': '#00E5FF',
        'genres': [
          {'genre': 'Dubstep & EDM', 'count': 400, 'color': '#00E5FF', 'percent': 40.0}
        ],
      };
      final seg = TimelineSegment.fromJson(json);
      expect(seg.segmentIndex, 0);
      expect(seg.label, '#1–#1000');
      expect(seg.dominantGenre, 'Dubstep & EDM');
      expect(seg.genres.length, 1);
      expect(seg.genres.first.percent, 40.0);
    });
  });
}
