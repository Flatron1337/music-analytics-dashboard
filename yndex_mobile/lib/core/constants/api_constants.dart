class ApiConstants {
  // Default base URL (can be overwritten dynamically via settings)
  // For Android emulator: http://10.0.2.2:5001
  // For Windows desktop: http://localhost:5001
  // For physical device on Wi-Fi: http://<LAN_IP>:5001
  // For cloud: https://music-analytics-dashboard.onrender.com
  static const String defaultLocalHost = 'http://127.0.0.1:5001';
  static const String defaultAndroidEmulator = 'http://10.0.2.2:5001';
  static const String defaultRenderHost = 'https://music-analytics-dashboard.onrender.com';

  static const String prefServerUrlKey = 'custom_server_url';
  static const String prefYandexTokenKey = 'yandex_music_token';
  static const String prefCacheOverviewKey = 'cache_overview_json';
  static const String prefCacheGenresKey = 'cache_genres_json';
  static const String prefCacheTimelineKey = 'cache_timeline_json';

  // Endpoints
  static const String endpointHealth = '/api/health';
  static const String endpointOverview = '/api/overview';
  static const String endpointGenres = '/api/genres';
  static const String endpointTimeline = '/api/timeline';
  static const String endpointTracks = '/api/tracks';
  static const String endpointDeviceCode = '/api/auth/device-code';
  static const String endpointPollToken = '/api/auth/poll-token';
  static const String endpointSyncLikes = '/api/sync-likes';
  static const String endpointSyncLikesStream = '/api/sync-likes/stream';
  static const String endpointExportPlaylist = '/api/export-playlist';
  static const String endpointArtist = '/api/artist';
  static const String endpointCollaborationsGraph = '/api/collaborations-graph';
}
