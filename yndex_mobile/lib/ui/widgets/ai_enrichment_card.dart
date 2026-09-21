import 'dart:async';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/sync_progress_event.dart';
import '../../state/app_view_model.dart';

class AiEnrichmentCard extends StatefulWidget {
  final AppViewModel appViewModel;

  const AiEnrichmentCard({
    super.key,
    required this.appViewModel,
  });

  @override
  State<AiEnrichmentCard> createState() => _AiEnrichmentCardState();
}

class _AiEnrichmentCardState extends State<AiEnrichmentCard> {
  bool _isLoadingStatus = true;
  int _unresolvedCount = 0;

  bool _isRunning = false;
  double _progress = 0.0;
  String? _currentMessage;
  StreamSubscription<SyncProgressEvent>? _subscription;

  @override
  void initState() {
    super.initState();
    _fetchStatus();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  Future<void> _fetchStatus() async {
    setState(() => _isLoadingStatus = true);
    try {
      final res = await widget.appViewModel.apiService.getEnrichStatus();
      if (mounted) {
        setState(() {
          _unresolvedCount = res['unresolved_count'] as int? ?? 0;
          _isLoadingStatus = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoadingStatus = false);
      }
    }
  }

  void _startEnrichment() {
    setState(() {
      _isRunning = true;
      _progress = 0.02;
      _currentMessage = 'Подготовка AI-анализа...';
    });

    _subscription?.cancel();
    _subscription = widget.appViewModel.apiService.streamAiEnrichment().listen(
      (event) {
        if (!mounted) return;

        if (event.isError) {
          setState(() {
            _isRunning = false;
            _currentMessage = 'Ошибка: ${event.message}';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Ошибка AI: ${event.message}'),
              backgroundColor: AppColors.yandexRed,
            ),
          );
        } else if (event.isComplete) {
          setState(() {
            _isRunning = false;
            _progress = 1.0;
            _currentMessage = event.message;
            _unresolvedCount = 0;
          });
          widget.appViewModel.loadDashboardData(forceRefresh: true);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(event.message.isNotEmpty ? event.message : 'AI-классификация завершена!'),
              backgroundColor: AppColors.neonGreen,
              duration: const Duration(seconds: 4),
            ),
          );
        } else {
          setState(() {
            _progress = (event.percent / 100.0).clamp(0.0, 1.0);
            _currentMessage = event.message;
          });
        }
      },
      onError: (err) {
        if (!mounted) return;
        setState(() {
          _isRunning = false;
          _currentMessage = 'Сбой сети: $err';
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: AppColors.neonGreen.withValues(alpha: 0.4),
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.neonGreen.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.psychology_rounded, color: AppColors.neonGreen, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          'AI-доклассификация',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppColors.neonGreen.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Text(
                            'GEMINI + GROQ',
                            style: TextStyle(
                              color: AppColors.neonGreen,
                              fontSize: 9,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const Text(
                      'Нейросетевое распознавание андерграунд-треков',
                      style: TextStyle(color: AppColors.textMuted, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'Находит исполнителей, у которых нет информации на Last.fm, и распределяет их по точным жанровым кластерам на основе названий треков:',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 12),

          // Unresolved count badge
          if (_isLoadingStatus)
            const Row(
              children: [
                SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                SizedBox(width: 8),
                Text('Проверка базы кэша...', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
              ],
            )
          else ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceElevated,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.cardBorder),
              ),
              child: Row(
                children: [
                  Icon(
                    _unresolvedCount > 0 ? Icons.info_outline_rounded : Icons.check_circle_outline_rounded,
                    size: 16,
                    color: _unresolvedCount > 0 ? AppColors.yandexAmber : AppColors.neonGreen,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _unresolvedCount > 0
                        ? '$_unresolvedCount артистов без жанровых тегов'
                        : 'Все артисты классифицированы!',
                    style: TextStyle(
                      color: _unresolvedCount > 0 ? AppColors.yandexAmber : AppColors.neonGreen,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),

          // Running Progress
          if (_isRunning) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: _progress,
                minHeight: 8,
                backgroundColor: AppColors.surfaceElevated,
                color: AppColors.neonGreen,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    _currentMessage ?? 'Выполняется AI-анализ...',
                    style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Text(
                  '${(_progress * 100).toInt()}%',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.neonGreen),
                ),
              ],
            ),
            const SizedBox(height: 14),
          ],

          // Action Button
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _isRunning || (_unresolvedCount == 0 && !_isLoadingStatus) ? null : _startEnrichment,
              icon: _isRunning
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                    )
                  : const Icon(Icons.auto_awesome_rounded),
              label: Text(_isRunning
                  ? 'AI-анализ выполняется...'
                  : _unresolvedCount == 0 && !_isLoadingStatus
                      ? 'Медиатека полностью обогащена'
                      : 'Запустить AI-доклассификацию'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.neonGreen,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
