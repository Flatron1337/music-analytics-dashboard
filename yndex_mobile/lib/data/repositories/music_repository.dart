import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/constants/api_constants.dart';
import '../models/overview_stats.dart';
import '../models/genre_cluster.dart';
import '../models/timeline_point.dart';
import '../services/api_service.dart';

class MusicRepository {
  final ApiService _apiService;

  OverviewStats? _cachedOverview;
  List<GenreCluster>? _cachedGenres;
  List<TimelineSegment>? _cachedTimeline;

  MusicRepository({ApiService? apiService}) : _apiService = apiService ?? ApiService();

  ApiService get apiService => _apiService;

  OverviewStats? get cachedOverview => _cachedOverview;
  List<GenreCluster>? get cachedGenres => _cachedGenres;
  List<TimelineSegment>? get cachedTimeline => _cachedTimeline;
  bool get hasOfflineCache => _cachedOverview != null;

  /// Loads locally cached data from SharedPreferences for instant 0ms cold-start.
  Future<void> loadFromLocalCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      final overviewRaw = prefs.getString(ApiConstants.prefCacheOverviewKey);
      if (overviewRaw != null && overviewRaw.isNotEmpty) {
        final data = jsonDecode(overviewRaw) as Map<String, dynamic>;
        _cachedOverview = OverviewStats.fromJson(data);
      }

      final genresRaw = prefs.getString(ApiConstants.prefCacheGenresKey);
      if (genresRaw != null && genresRaw.isNotEmpty) {
        final data = jsonDecode(genresRaw) as Map<String, dynamic>;
        final rawList = data['clusters'] as List<dynamic>? ?? [];
        _cachedGenres = rawList.map((e) => GenreCluster.fromJson(e as Map<String, dynamic>)).toList();
      }

      final timelineRaw = prefs.getString(ApiConstants.prefCacheTimelineKey);
      if (timelineRaw != null && timelineRaw.isNotEmpty) {
        final data = jsonDecode(timelineRaw) as Map<String, dynamic>;
        final rawList = data['segments'] as List<dynamic>? ?? [];
        _cachedTimeline = rawList.map((e) => TimelineSegment.fromJson(e as Map<String, dynamic>)).toList();
      }
    } catch (_) {
      // In case of parsing error on corrupted cache, continue gracefully
    }
  }

  Future<OverviewStats> getOverview({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedOverview != null) {
      return _cachedOverview!;
    }
    try {
      final data = await _apiService.fetchOverview();
      _cachedOverview = data;
      return data;
    } catch (e) {
      // If we have cached data, return it even if network failed
      if (_cachedOverview != null) {
        return _cachedOverview!;
      }
      rethrow;
    }
  }

  Future<List<GenreCluster>> getGenres({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedGenres != null) {
      return _cachedGenres!;
    }
    try {
      final data = await _apiService.fetchGenres();
      _cachedGenres = data;
      return data;
    } catch (e) {
      if (_cachedGenres != null) {
        return _cachedGenres!;
      }
      rethrow;
    }
  }

  Future<List<TimelineSegment>> getTimeline({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedTimeline != null) {
      return _cachedTimeline!;
    }
    try {
      final data = await _apiService.fetchTimeline();
      _cachedTimeline = data;
      return data;
    } catch (e) {
      if (_cachedTimeline != null) {
        return _cachedTimeline!;
      }
      rethrow;
    }
  }

  void clearCache() {
    _cachedOverview = null;
    _cachedGenres = null;
    _cachedTimeline = null;
  }
}

