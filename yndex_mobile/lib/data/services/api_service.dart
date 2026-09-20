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
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
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
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
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
      final data = jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
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
}
