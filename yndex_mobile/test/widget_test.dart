import 'package:flutter_test/flutter_test.dart';
import 'package:yndex_mobile/data/models/genre_cluster.dart';
import 'package:yndex_mobile/data/models/overview_stats.dart';
import 'package:yndex_mobile/data/models/track_item.dart';
import 'package:yndex_mobile/data/models/timeline_point.dart';
import 'package:yndex_mobile/data/models/collab_graph.dart';
import 'package:yndex_mobile/data/models/sync_progress_event.dart';
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

    test('CollabGraphData and GraphNode fromJson test', () {
      final json = {
        'nodes': [
          {
            'id': 'Skrillex',
            'name': 'Skrillex',
            'tracks_count': 120,
            'degree': 14,
            'dominant_genre': 'Dubstep & EDM',
            'color': '#00E5FF',
            'x': 0.25,
            'y': -0.45,
          },
          {
            'id': 'Diplo',
            'name': 'Diplo',
            'tracks_count': 45,
            'degree': 8,
            'dominant_genre': 'Dubstep & EDM',
            'color': '#00E5FF',
            'x': -0.15,
            'y': 0.35,
          }
        ],
        'edges': [
          {
            'source': 'Skrillex',
            'target': 'Diplo',
            'weight': 3,
          }
        ],
        'stats': {
          'total_nodes': 2,
          'total_edges': 1,
          'min_collaborations': 1,
          'focus_artist': null,
        }
      };

      final graph = CollabGraphData.fromJson(json);
      expect(graph.nodes.length, 2);
      expect(graph.edges.length, 1);
      expect(graph.totalNodes, 2);
      expect(graph.totalEdges, 1);

      final node = graph.nodes.first;
      expect(node.id, 'Skrillex');
      expect(node.name, 'Skrillex');
      expect(node.tracksCount, 120);
      expect(node.degree, 14);
      expect(node.x, 0.25);
      expect(node.y, -0.45);

      final edge = graph.edges.first;
      expect(edge.source, 'Skrillex');
      expect(edge.target, 'Diplo');
      expect(edge.weight, 3);
    });

    test('SyncProgressEvent fromJson test', () {
      final progressJson = {
        'type': 'progress',
        'stage': 'fetching',
        'percent': 45,
        'current': 45,
        'total': 100,
        'message': 'Загрузка метаданных...',
      };
      final progressEvent = SyncProgressEvent.fromJson(progressJson);
      expect(progressEvent.type, 'progress');
      expect(progressEvent.stage, 'fetching');
      expect(progressEvent.percent, 45);
      expect(progressEvent.isComplete, false);
      expect(progressEvent.isError, false);

      final completeJson = {
        'type': 'complete',
        'stage': 'done',
        'percent': 100,
        'current': 9006,
        'total': 9006,
        'tracks_synced': 9006,
        'message': 'Синхронизировано 9,006 треков!',
      };
      final completeEvent = SyncProgressEvent.fromJson(completeJson);
      expect(completeEvent.isComplete, true);
      expect(completeEvent.tracksSynced, 9006);
    });
  });
}
