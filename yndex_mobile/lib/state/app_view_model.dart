import 'package:flutter/material.dart';
import '../data/models/overview_stats.dart';
import '../data/models/genre_cluster.dart';
import '../data/models/track_item.dart';
import '../data/models/timeline_point.dart';
import '../data/repositories/music_repository.dart';

class AppViewModel extends ChangeNotifier {
  final MusicRepository repository;

  AppViewModel({required this.repository});

  int _selectedTabIndex = 0;
  int get selectedTabIndex => _selectedTabIndex;

  bool _isServerConnected = false;
  bool get isServerConnected => _isServerConnected;

  String _serverUrl = '';
  String get serverUrl => _serverUrl;

  // Overview
  OverviewStats? _overviewStats;
  OverviewStats? get overviewStats => _overviewStats;
  bool _isLoadingOverview = false;
  bool get isLoadingOverview => _isLoadingOverview;
  String? _overviewError;
  String? get overviewError => _overviewError;

  // Genres
  List<GenreCluster> _genres = [];
  List<GenreCluster> get genres => _genres;
  bool _isLoadingGenres = false;
  bool get isLoadingGenres => _isLoadingGenres;

  // Timeline
  List<TimelineSegment> _timeline = [];
  List<TimelineSegment> get timeline => _timeline;
  bool _isLoadingTimeline = false;
  bool get isLoadingTimeline => _isLoadingTimeline;

  // Tracks
  List<TrackItem> _tracks = [];
  List<TrackItem> get tracks => _tracks;
  bool _isLoadingTracks = false;
  bool get isLoadingTracks => _isLoadingTracks;
  int _tracksPage = 1;
  int get tracksPage => _tracksPage;
  int _tracksTotalPages = 1;
  int get tracksTotalPages => _tracksTotalPages;
  int _totalTracksFound = 0;
  int get totalTracksFound => _totalTracksFound;
  String _searchQuery = '';
  String get searchQuery => _searchQuery;
  String _selectedGenreFilter = 'Все';
  String get selectedGenreFilter => _selectedGenreFilter;

  void setTab(int index) {
    _selectedTabIndex = index;
    notifyListeners();
  }

  Future<void> init() async {
    _serverUrl = await repository.apiService.baseUrl;
    await checkConnection();
    if (_isServerConnected) {
      await loadDashboardData();
    }
  }

  Future<void> checkConnection() async {
    _isServerConnected = await repository.apiService.checkHealth();
    notifyListeners();
  }

  Future<void> updateServerUrl(String newUrl) async {
    await repository.apiService.setCustomBaseUrl(newUrl);
    _serverUrl = await repository.apiService.baseUrl;
    repository.clearCache();
    await checkConnection();
    if (_isServerConnected) {
      await loadDashboardData(forceRefresh: true);
    }
  }

  Future<void> loadDashboardData({bool forceRefresh = false}) async {
    await Future.wait([
      loadOverview(forceRefresh: forceRefresh),
      loadGenres(forceRefresh: forceRefresh),
      loadTimeline(forceRefresh: forceRefresh),
      loadTracks(resetPage: true),
    ]);
  }

  Future<void> loadOverview({bool forceRefresh = false}) async {
    _isLoadingOverview = true;
    _overviewError = null;
    notifyListeners();

    try {
      _overviewStats = await repository.getOverview(forceRefresh: forceRefresh);
      _isServerConnected = true;
    } catch (e) {
      _overviewError = e.toString().replaceFirst('Exception: ', '');
      _isServerConnected = false;
    } finally {
      _isLoadingOverview = false;
      notifyListeners();
    }
  }

  Future<void> loadGenres({bool forceRefresh = false}) async {
    _isLoadingGenres = true;
    notifyListeners();

    try {
      _genres = await repository.getGenres(forceRefresh: forceRefresh);
    } catch (_) {
      _genres = [];
    } finally {
      _isLoadingGenres = false;
      notifyListeners();
    }
  }

  Future<void> loadTimeline({bool forceRefresh = false}) async {
    _isLoadingTimeline = true;
    notifyListeners();

    try {
      _timeline = await repository.getTimeline(forceRefresh: forceRefresh);
    } catch (_) {
      _timeline = [];
    } finally {
      _isLoadingTimeline = false;
      notifyListeners();
    }
  }

  Future<void> loadTracks({bool resetPage = false}) async {
    if (resetPage) {
      _tracksPage = 1;
      _tracks = [];
    }
    _isLoadingTracks = true;
    notifyListeners();

    try {
      final res = await repository.apiService.fetchTracks(
        query: _searchQuery,
        genre: _selectedGenreFilter == 'Все' ? '' : _selectedGenreFilter,
        page: _tracksPage,
        limit: 40,
      );
      _tracks = res['tracks'] as List<TrackItem>;
      _totalTracksFound = res['total'] as int;
      _tracksPage = res['page'] as int;
      _tracksTotalPages = res['total_pages'] as int;
    } catch (_) {
      _tracks = [];
    } finally {
      _isLoadingTracks = false;
      notifyListeners();
    }
  }

  void setSearchQuery(String query) {
    if (_searchQuery == query) return;
    _searchQuery = query;
    loadTracks(resetPage: true);
  }

  void setGenreFilter(String genre) {
    if (_selectedGenreFilter == genre) return;
    _selectedGenreFilter = genre;
    loadTracks(resetPage: true);
  }

  void nextPage() {
    if (_tracksPage < _tracksTotalPages && !_isLoadingTracks) {
      _tracksPage++;
      loadTracks();
    }
  }

  void prevPage() {
    if (_tracksPage > 1 && !_isLoadingTracks) {
      _tracksPage--;
      loadTracks();
    }
  }
}
