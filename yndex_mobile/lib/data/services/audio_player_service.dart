import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';

class AudioPlayerService extends ChangeNotifier {
  static final AudioPlayerService _instance = AudioPlayerService._internal();
  factory AudioPlayerService() => _instance;

  final AudioPlayer _player = AudioPlayer();

  String? _currentTrackId;
  String? _currentTitle;
  String? _currentArtist;
  String? _currentCoverUrl;
  bool _isPlaying = false;
  bool _isLoading = false;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  String? _errorMessage;

  StreamSubscription? _stateSubscription;
  StreamSubscription? _positionSubscription;
  StreamSubscription? _durationSubscription;

  AudioPlayerService._internal() {
    _initListeners();
  }

  void _initListeners() {
    _stateSubscription = _player.onPlayerStateChanged.listen((state) {
      _isPlaying = state == PlayerState.playing;
      _isLoading = false;
      notifyListeners();
    });

    _positionSubscription = _player.onPositionChanged.listen((pos) {
      _position = pos;
      notifyListeners();
    });

    _durationSubscription = _player.onDurationChanged.listen((dur) {
      _duration = dur;
      notifyListeners();
    });

    _player.onPlayerComplete.listen((_) {
      _isPlaying = false;
      _position = Duration.zero;
      notifyListeners();
    });
  }

  String? get currentTrackId => _currentTrackId;
  String? get currentTitle => _currentTitle;
  String? get currentArtist => _currentArtist;
  String? get currentCoverUrl => _currentCoverUrl;
  bool get isPlaying => _isPlaying;
  bool get isLoading => _isLoading;
  Duration get position => _position;
  Duration get duration => _duration;
  String? get errorMessage => _errorMessage;

  bool isTrackActive(String trackId) => _currentTrackId == trackId;
  bool isTrackPlaying(String trackId) => _currentTrackId == trackId && _isPlaying;
  bool isTrackLoading(String trackId) => _currentTrackId == trackId && _isLoading;

  Future<void> playTrack({
    required String trackId,
    required String title,
    required String artist,
    String? coverUrl,
    required String streamUrl,
  }) async {
    // If same track is already playing, pause it
    if (_currentTrackId == trackId && _isPlaying) {
      await pause();
      return;
    }

    // If same track is paused, resume it
    if (_currentTrackId == trackId && !_isPlaying && _position > Duration.zero) {
      await resume();
      return;
    }

    try {
      _currentTrackId = trackId;
      _currentTitle = title;
      _currentArtist = artist;
      _currentCoverUrl = coverUrl;
      _isLoading = true;
      _errorMessage = null;
      _position = Duration.zero;
      notifyListeners();

      await _player.stop();
      await _player.play(UrlSource(streamUrl));
    } catch (e) {
      _isLoading = false;
      _isPlaying = false;
      _errorMessage = 'Ошибка воспроизведения: $e';
      notifyListeners();
    }
  }

  Future<void> pause() async {
    try {
      await _player.pause();
    } catch (_) {}
  }

  Future<void> resume() async {
    try {
      await _player.resume();
    } catch (_) {}
  }

  Future<void> togglePlayPause() async {
    if (_isPlaying) {
      await pause();
    } else {
      await resume();
    }
  }

  Future<void> stop() async {
    try {
      await _player.stop();
      _currentTrackId = null;
      _currentTitle = null;
      _currentArtist = null;
      _currentCoverUrl = null;
      _isPlaying = false;
      _isLoading = false;
      _position = Duration.zero;
      _duration = Duration.zero;
      notifyListeners();
    } catch (_) {}
  }

  Future<void> seek(Duration pos) async {
    try {
      await _player.seek(pos);
    } catch (_) {}
  }

  @override
  void dispose() {
    _stateSubscription?.cancel();
    _positionSubscription?.cancel();
    _durationSubscription?.cancel();
    _player.dispose();
    super.dispose();
  }
}
