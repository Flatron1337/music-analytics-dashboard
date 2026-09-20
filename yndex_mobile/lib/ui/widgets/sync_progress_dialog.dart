import 'dart:async';
import 'package:flutter/material.dart';
import '../../data/models/sync_progress_event.dart';
import '../../data/services/api_service.dart';

class SyncProgressDialog extends StatefulWidget {
  final String token;
  final VoidCallback? onComplete;

  const SyncProgressDialog({
    super.key,
    required this.token,
    this.onComplete,
  });

  @override
  State<SyncProgressDialog> createState() => _SyncProgressDialogState();
}

class _SyncProgressDialogState extends State<SyncProgressDialog>
    with SingleTickerProviderStateMixin {
  final ApiService _apiService = ApiService();
  StreamSubscription<SyncProgressEvent>? _subscription;

  int _percent = 0;
  String _message = 'Инициализация синхронизации...';
  String _stage = 'init';
  bool _isComplete = false;
  bool _isError = false;
  String? _errorMessage;
  int? _tracksSynced;

  late AnimationController _animController;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();

    _startListening();
  }

  void _startListening() {
    _subscription = _apiService.streamSyncLikes(widget.token).listen(
      (event) {
        if (!mounted) return;
        setState(() {
          _percent = event.percent;
          _message = event.message;
          _stage = event.stage;

          if (event.isComplete) {
            _isComplete = true;
            _tracksSynced = event.tracksSynced;
            _animController.stop();
          } else if (event.isError) {
            _isError = true;
            _errorMessage = event.message;
            _animController.stop();
          }
        });
      },
      onError: (err) {
        if (!mounted) return;
        setState(() {
          _isError = true;
          _errorMessage = 'Ошибка соединения: $err';
          _animController.stop();
        });
      },
    );
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _animController.dispose();
    super.dispose();
  }

  String _getStageTitle() {
    if (_isComplete) return 'Синхронизация завершена!';
    if (_isError) return 'Ошибка синхронизации';
    switch (_stage) {
      case 'auth':
        return 'Авторизация в Яндекс Музыке';
      case 'fetching_init':
      case 'fetching':
        return 'Загрузка треков и метаданных';
      case 'classifying':
        return 'Классификация жанров';
      default:
        return 'Синхронизация медиатеки...';
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: _isComplete || _isError,
      child: Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF161B22),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: _isError
                  ? Colors.redAccent.withValues(alpha: 0.5)
                  : _isComplete
                      ? const Color(0xFF00E676).withValues(alpha: 0.5)
                      : const Color(0xFF00E5FF).withValues(alpha: 0.3),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: _isError
                    ? Colors.redAccent.withValues(alpha: 0.2)
                    : _isComplete
                        ? const Color(0xFF00E676).withValues(alpha: 0.25)
                        : const Color(0xFF00E5FF).withValues(alpha: 0.2),
                blurRadius: 30,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildHeaderIcon(),
              const SizedBox(height: 18),

              Text(
                _getStageTitle(),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 10),

              Text(
                _isError
                    ? (_errorMessage ?? _message)
                    : (_isComplete && _tracksSynced != null
                        ? 'Успешно обновлено: $_tracksSynced треков в медиатеке!'
                        : _message),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: _isError
                      ? Colors.red[300]
                      : Colors.white.withValues(alpha: 0.75),
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 24),

              if (!_isError) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      _isComplete ? 'Готово' : 'Прогресс',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 12,
                      ),
                    ),
                    Text(
                      '$_percent%',
                      style: const TextStyle(
                        color: Color(0xFF00E5FF),
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Stack(
                    children: [
                      Container(
                        height: 10,
                        width: double.infinity,
                        color: Colors.white.withValues(alpha: 0.08),
                      ),
                      AnimatedFractionallySizedBox(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeOutCubic,
                        widthFactor: (_percent / 100).clamp(0.0, 1.0),
                        child: Container(
                          height: 10,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: _isComplete
                                  ? [
                                      const Color(0xFF00E676),
                                      const Color(0xFF00B0FF),
                                    ]
                                  : [
                                      const Color(0xFF00E5FF),
                                      const Color(0xFFD500F9),
                                    ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],

              if (_isComplete) ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pop();
                      widget.onComplete?.call();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF00E676),
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                      elevation: 0,
                    ),
                    child: const Text(
                      'Отлично, перейти к коллекции',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ),
              ] else if (_isError) ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white.withValues(alpha: 0.12),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    child: const Text(
                      'Закрыть',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderIcon() {
    if (_isComplete) {
      return Container(
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          color: const Color(0xFF00E676).withValues(alpha: 0.15),
          shape: BoxShape.circle,
          border: Border.all(color: const Color(0xFF00E676), width: 2),
        ),
        child: const Icon(
          Icons.check_circle_rounded,
          color: Color(0xFF00E676),
          size: 36,
        ),
      );
    }

    if (_isError) {
      return Container(
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          color: Colors.redAccent.withValues(alpha: 0.15),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.redAccent, width: 2),
        ),
        child: const Icon(
          Icons.error_outline_rounded,
          color: Colors.redAccent,
          size: 36,
        ),
      );
    }

    return RotationTransition(
      turns: _animController,
      child: Container(
        width: 64,
        height: 64,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: SweepGradient(
            colors: [
              const Color(0xFF00E5FF).withValues(alpha: 0.1),
              const Color(0xFF00E5FF),
              const Color(0xFFD500F9),
              const Color(0xFF00E5FF).withValues(alpha: 0.1),
            ],
          ),
        ),
        padding: const EdgeInsets.all(3),
        child: Container(
          decoration: const BoxDecoration(
            color: Color(0xFF161B22),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.sync_rounded,
            color: Color(0xFF00E5FF),
            size: 30,
          ),
        ),
      ),
    );
  }
}
