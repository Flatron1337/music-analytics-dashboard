import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/constants/api_constants.dart';
import '../models/overview_stats.dart';
import '../models/genre_cluster.dart';
import '../models/track_item.dart';
import '../models/timeline_point.dart';
import '../models/artist_details.dart';
import '../models/collab_graph.dart';
import '../models/sync_progress_event.dart';
import '../models/duplicates_data.dart';
import '../models/audio_features_data.dart';

class ApiService {
  String? _customBaseUrl;

  Future<String> get baseUrl async {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(ApiConstants.prefServerUrlKey);
    if (saved != null && saved.isNotEmpty) {
      _customBaseUrl = saved;
      return saved;
    }

    // Smart default detection based on platform
    if (!kIsWeb && Platform.isAndroid) {
      // In Android emulator, 10.0.2.2 maps to host PC 127.0.0.1
      return ApiConstants.defaultAndroidEmulator;
    }
    return ApiConstants.defaultLocalHost;
  }

  Future<void> setCustomBaseUrl(String url) async {
    String cleanUrl = url.trim();
    if (cleanUrl.endsWith('/')) {
      cleanUrl = cleanUrl.substring(0, cleanUrl.length - 1);
    }
    _customBaseUrl = cleanUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiConstants.prefServerUrlKey, cleanUrl);
  }

  Future<bool> checkHealth() async {
    try {
      final host = await baseUrl;
      final uri = Uri.parse('$host${ApiConstants.endpointHealth}');
      final response = await http.get(uri).timeout(const Duration(seconds: 6));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<OverviewStats> fetchOverview() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointOverview}');
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final jsonStr = utf8.decode(response.bodyBytes);
      final data = jsonDecode(jsonStr) as Map<String, dynamic>;
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(ApiConstants.prefCacheOverviewKey, jsonStr);
      } catch (_) {}
      return OverviewStats.fromJson(data);
    } else {
      throw Exception('Ошибка загрузки статистики (${response.statusCode})');
    }
  }

  Future<List<GenreCluster>> fetchGenres() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointGenres}');
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final jsonStr = utf8.decode(response.bodyBytes);
      final data = jsonDecode(jsonStr) as Map<String, dynamic>;
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(ApiConstants.prefCacheGenresKey, jsonStr);
      } catch (_) {}
      final rawList = data['clusters'] as List<dynamic>? ?? [];
      return rawList.map((e) => GenreCluster.fromJson(e as Map<String, dynamic>)).toList();
    } else {
      throw Exception('Ошибка загрузки жанров (${response.statusCode})');
    }
  }

  Future<List<TimelineSegment>> fetchTimeline() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointTimeline}');
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final jsonStr = utf8.decode(response.bodyBytes);
      final data = jsonDecode(jsonStr) as Map<String, dynamic>;
      try {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(ApiConstants.prefCacheTimelineKey, jsonStr);
      } catch (_) {}
      final rawList = data['segments'] as List<dynamic>? ?? [];
      return rawList.map((e) => TimelineSegment.fromJson(e as Map<String, dynamic>)).toList();
    } else {
      throw Exception('Ошибка загрузки таймлайна (${response.statusCode})');
    }
  }

  Future<Map<String, dynamic>> fetchTracks({
    String query = '',
    String genre = '',
    String sortBy = 'newest',
    String collabFilter = 'all',
    int page = 1,
    int limit = 40,
  }) async {
    final host = await baseUrl;
    final queryParams = <String, String>{
      'page': page.toString(),
      'limit': limit.toString(),
    };
    if (query.isNotEmpty) queryParams['q'] = query;
    if (genre.isNotEmpty && genre != 'Все') queryParams['genre'] = genre;
    if (sortBy.isNotEmpty && sortBy != 'newest') queryParams['sort'] = sortBy;
    if (collabFilter.isNotEmpty && collabFilter != 'all') queryParams['collab'] = collabFilter;

    final uri = Uri.parse('$host${ApiConstants.endpointTracks}').replace(queryParameters: queryParams);
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      final rawList = data['tracks'] as List<dynamic>? ?? [];
      final tracks = rawList.map((e) => TrackItem.fromJson(e as Map<String, dynamic>)).toList();
      return {
        'tracks': tracks,
        'total': data['total'] as int? ?? 0,
        'page': data['page'] as int? ?? 1,
        'total_pages': data['total_pages'] as int? ?? 1,
      };
    } else {
      throw Exception('Ошибка загрузки треков (${response.statusCode})');
    }
  }

  Future<Map<String, dynamic>> requestDeviceCode() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointDeviceCode}');
    final response = await http.post(uri).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } else {
      throw Exception('Не удалось запросить код авторизации');
    }
  }

  Future<Map<String, dynamic>> pollDeviceToken(String deviceCode) async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointPollToken}');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'device_code': deviceCode}),
    ).timeout(const Duration(seconds: 10));

    return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> syncLikes(String token) async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointSyncLikes}');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'token': token}),
    ).timeout(const Duration(seconds: 45));

    final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    if (response.statusCode == 200 && data['success'] == true) {
      return data;
    } else {
      throw Exception(data['error'] ?? 'Ошибка синхронизации лайков');
    }
  }

  Future<Map<String, dynamic>> exportPlaylist({
    required String token,
    required String preset,
    String? genre,
    String? title,
    int limit = 100,
  }) async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointExportPlaylist}');
    final payload = <String, dynamic>{
      'token': token,
      'preset': preset,
      'limit': limit,
    };
    if (genre != null && genre.isNotEmpty) {
      payload['genre'] = genre;
    }
    if (title != null && title.isNotEmpty) {
      payload['title'] = title;
    }

    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    ).timeout(const Duration(seconds: 60));

    final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    if (response.statusCode == 200 && data['success'] == true) {
      return data;
    } else {
      throw Exception(data['error'] ?? 'Не удалось экспортировать плейлист');
    }
  }

  Future<ArtistDetails> fetchArtistDetails(String name) async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointArtist}').replace(queryParameters: {'name': name});
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return ArtistDetails.fromJson(data);
    } else {
      try {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        throw Exception(data['error'] ?? 'Ошибка загрузки артиста');
      } catch (_) {
        throw Exception('Ошибка загрузки данных артиста (${response.statusCode})');
      }
    }
  }

  Future<CollabGraphData> fetchCollaborationsGraph({
    int minCollabs = 1,
    int limitNodes = 60,
    String? focusArtist,
  }) async {
    final host = await baseUrl;
    final query = <String, String>{
      'min_collabs': minCollabs.toString(),
      'limit_nodes': limitNodes.toString(),
    };
    if (focusArtist != null && focusArtist.isNotEmpty) {
      query['focus_artist'] = focusArtist;
    }

    final uri = Uri.parse('$host${ApiConstants.endpointCollaborationsGraph}').replace(
      queryParameters: query,
    );
    final response = await http.get(uri).timeout(const Duration(seconds: 25));

    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return CollabGraphData.fromJson(data);
    } else {
      throw Exception('Не удалось загрузить граф связей (${response.statusCode})');
    }
  }

  Stream<SyncProgressEvent> streamSyncLikes(String token) async* {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointSyncLikesStream}').replace(
      queryParameters: {'token': token},
    );

    final client = http.Client();
    try {
      final request = http.Request('GET', uri);
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final streamedResponse = await client.send(request).timeout(const Duration(seconds: 60));

      if (streamedResponse.statusCode != 200) {
        final errorBody = await streamedResponse.stream.bytesToString();
        try {
          final errJson = jsonDecode(errorBody);
          yield SyncProgressEvent.error(
            errJson['error'] ?? 'Ошибка подключения (${streamedResponse.statusCode})',
          );
        } catch (_) {
          yield SyncProgressEvent.error(
            'Ошибка подключения к серверу (${streamedResponse.statusCode})',
          );
        }
        return;
      }

      String buffer = '';
      await for (final chunk in streamedResponse.stream.transform(utf8.decoder)) {
        buffer += chunk;
        while (buffer.contains('\n\n')) {
          final eventEnd = buffer.indexOf('\n\n');
          final rawBlock = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);

          final lines = rawBlock.split('\n');
          String? dataStr;

          for (final line in lines) {
            final trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              dataStr = trimmed.substring(5).trim();
            }
          }

          if (dataStr != null && dataStr.isNotEmpty) {
            try {
              final json = jsonDecode(dataStr) as Map<String, dynamic>;
              yield SyncProgressEvent.fromJson(json);
            } catch (_) {}
          }
        }
      }
    } catch (e) {
      yield SyncProgressEvent.error('Сбой передачи данных: $e');
    } finally {
      client.close();
    }
  }

  Future<Map<String, dynamic>> getEnrichStatus() async {
    try {
      final host = await baseUrl;
      final url = Uri.parse('$host${ApiConstants.endpointEnrichGenresStatus}');
      final response = await http.get(url).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (_) {}
    return {'unresolved_count': 0, 'is_configured': false};
  }

  Stream<SyncProgressEvent> streamAiEnrichment() async* {
    final host = await baseUrl;
    final url = Uri.parse('$host${ApiConstants.endpointEnrichGenresStream}');
    final client = http.Client();

    try {
      final request = http.Request('GET', url);
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final streamedResponse = await client.send(request).timeout(const Duration(seconds: 60));

      if (streamedResponse.statusCode != 200) {
        final errorBody = await streamedResponse.stream.bytesToString();
        yield SyncProgressEvent.error('Ошибка сервера (${streamedResponse.statusCode}): $errorBody');
        return;
      }

      String buffer = '';
      await for (final chunk in streamedResponse.stream.transform(utf8.decoder)) {
        buffer += chunk;
        while (buffer.contains('\n\n')) {
          final splitIndex = buffer.indexOf('\n\n');
          final eventBlock = buffer.substring(0, splitIndex);
          buffer = buffer.substring(splitIndex + 2);

          final lines = eventBlock.split('\n');
          String? dataStr;

          for (final line in lines) {
            final trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              dataStr = trimmed.substring(5).trim();
            }
          }

          if (dataStr != null && dataStr.isNotEmpty) {
            try {
              final json = jsonDecode(dataStr) as Map<String, dynamic>;
              yield SyncProgressEvent.fromJson(json);
            } catch (_) {}
          }
        }
      }
    } catch (e) {
      yield SyncProgressEvent.error('Сбой передачи данных AI: $e');
    } finally {
      client.close();
    }
  }

  Future<String?> getYandexToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(ApiConstants.prefYandexTokenKey);
  }

  Future<String?> fetchTrackStream(
    String trackId, {
    String? title,
    String? artist,
  }) async {
    final host = await baseUrl;
    final token = await getYandexToken();
    final queryParams = <String, String>{};
    if (title != null && title.isNotEmpty) queryParams['title'] = title;
    if (artist != null && artist.isNotEmpty) queryParams['artist'] = artist;

    final baseUri = Uri.parse('$host${ApiConstants.endpointTrackStream}/$trackId');
    final uri = queryParams.isNotEmpty
        ? baseUri.replace(queryParameters: queryParams)
        : baseUri;

    final headers = <String, String>{};
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    try {
      final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return data['stream_url']?.toString();
      }
    } catch (e) {
      debugPrint('Error fetching track stream for $trackId: $e');
    }
    return null;
  }

  Future<DuplicatesData> fetchDuplicates() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointDuplicates}');
    final response = await http.get(uri).timeout(const Duration(seconds: 15));

    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return DuplicatesData.fromJson(data);
    } else {
      throw Exception('Не удалось загрузить дубликаты (${response.statusCode})');
    }
  }

  Future<AudioFeaturesData> fetchAudioFeatures() async {
    final host = await baseUrl;
    final uri = Uri.parse('$host${ApiConstants.endpointAudioFeatures}');
    final response = await http.get(uri).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      return AudioFeaturesData.fromJson(data);
    } else {
      throw Exception('Не удалось загрузить аудио-характеристики (${response.statusCode})');
    }
  }

  Future<String> getGraphExportHtmlUrl({int minCollabs = 1, int limitNodes = 75}) async {
    final host = await baseUrl;
    return '$host${ApiConstants.endpointGraphExportHtml}?min_collabs=$minCollabs&limit_nodes=$limitNodes';
  }
}
