import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/api_constants.dart';
import '../data/services/api_service.dart';

class YandexAuthViewModel extends ChangeNotifier {
  final ApiService apiService;

  String? _userCode;
  String? get userCode => _userCode;

  String? _deviceCode;
  String? _verificationUrl;
  String? get verificationUrl => _verificationUrl;

  int _intervalSeconds = 5;
  Timer? _pollingTimer;

  bool _isRequestingCode = false;
  bool get isRequestingCode => _isRequestingCode;

  bool _isPolling = false;
  bool get isPolling => _isPolling;

  bool _isSyncing = false;
  bool get isSyncing => _isSyncing;

  String? _savedToken;
  String? get savedToken => _savedToken;

  String? _statusMessage;
  String? get statusMessage => _statusMessage;

  bool get isAuthenticated => _savedToken != null && _savedToken!.isNotEmpty;

  YandexAuthViewModel({required this.apiService}) {
    _loadSavedToken();
  }

  Future<void> _loadSavedToken() async {
    final prefs = await SharedPreferences.getInstance();
    _savedToken = prefs.getString(ApiConstants.prefYandexTokenKey);
    notifyListeners();
  }

  Future<void> startDeviceFlow() async {
    _cancelPolling();
    _isRequestingCode = true;
    _statusMessage = 'Запрос кода авторизации...';
    notifyListeners();

    try {
      final res = await apiService.requestDeviceCode();
      if (res['success'] == true) {
        _userCode = res['user_code'];
        _deviceCode = res['device_code'];
        _verificationUrl = res['verification_url'] ?? 'https://ya.ru/device';
        _intervalSeconds = (res['interval'] as num?)?.toInt() ?? 5;
        _statusMessage = 'Введите код на странице ya.ru/device';
        _isRequestingCode = false;
        notifyListeners();

        _startPolling();
      } else {
        _statusMessage = res['error'] ?? 'Ошибка запроса кода';
        _isRequestingCode = false;
        notifyListeners();
      }
    } catch (e) {
      _statusMessage = 'Сетевая ошибка: $e';
      _isRequestingCode = false;
      notifyListeners();
    }
  }

  void _startPolling() {
    _cancelPolling();
    if (_deviceCode == null) return;

    _isPolling = true;
    notifyListeners();

    _pollingTimer = Timer.periodic(Duration(seconds: _intervalSeconds), (timer) async {
      try {
        final res = await apiService.pollDeviceToken(_deviceCode!);
        if (res['status'] == 'success') {
          _cancelPolling();
          final token = res['token'];
          await _saveToken(token);
          _statusMessage = 'Успешно авторизовано!';
          notifyListeners();
        } else if (res['status'] == 'authorization_pending') {
          // Keep polling
        } else if (res['status'] == 'slow_down') {
          _intervalSeconds += 5;
        } else {
          _cancelPolling();
          _statusMessage = res['message'] ?? 'Истекло время ожидания';
          notifyListeners();
        }
      } catch (_) {
        // Keep polling on transient network glitches
      }
    });
  }

  void _cancelPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _isPolling = false;
  }

  Future<void> _saveToken(String token) async {
    _savedToken = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ApiConstants.prefYandexTokenKey, token);
    notifyListeners();
  }

  Future<void> logout() async {
    _cancelPolling();
    _savedToken = null;
    _userCode = null;
    _deviceCode = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(ApiConstants.prefYandexTokenKey);
    _statusMessage = 'Вы вышли из аккаунта';
    notifyListeners();
  }

  Future<bool> syncLikes() async {
    if (_savedToken == null) return false;
    _isSyncing = true;
    _statusMessage = 'Синхронизация треков из Яндекс Музыки...';
    notifyListeners();

    try {
      final res = await apiService.syncLikes(_savedToken!);
      _statusMessage = res['message'] ?? 'Успешно синхронизировано!';
      _isSyncing = false;
      notifyListeners();
      return true;
    } catch (e) {
      _statusMessage = 'Ошибка: $e';
      _isSyncing = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> openVerificationUrl() async {
    final url = _verificationUrl ?? 'https://ya.ru/device';
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  void dispose() {
    _cancelPolling();
    super.dispose();
  }
}
