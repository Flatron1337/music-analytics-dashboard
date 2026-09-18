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

  Future<OverviewStats> getOverview({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedOverview != null) {
      return _cachedOverview!;
    }
    final data = await _apiService.fetchOverview();
    _cachedOverview = data;
    return data;
  }

  Future<List<GenreCluster>> getGenres({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedGenres != null) {
      return _cachedGenres!;
    }
    final data = await _apiService.fetchGenres();
    _cachedGenres = data;
    return data;
  }

  Future<List<TimelineSegment>> getTimeline({bool forceRefresh = false}) async {
    if (!forceRefresh && _cachedTimeline != null) {
      return _cachedTimeline!;
    }
    final data = await _apiService.fetchTimeline();
    _cachedTimeline = data;
    return data;
  }

  void clearCache() {
    _cachedOverview = null;
    _cachedGenres = null;
    _cachedTimeline = null;
  }
}
