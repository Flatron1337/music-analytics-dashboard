import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../state/app_view_model.dart';
import '../widgets/skeleton_loader.dart';

class TimelineTab extends StatelessWidget {
  final AppViewModel viewModel;

  const TimelineTab({super.key, required this.viewModel});

  @override
  Widget build(BuildContext context) {
    if (viewModel.isLoadingTimeline && viewModel.timeline.isEmpty) {
      return const TimelineSkeleton();
    }

    final segments = viewModel.timeline;
    if (segments.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.timeline_rounded, size: 64, color: AppColors.textMuted),
            const SizedBox(height: 16),
            const Text('Нет данных таймлайна'),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => viewModel.loadTimeline(forceRefresh: true),
              child: const Text('Загрузить'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => viewModel.loadTimeline(forceRefresh: true),
      color: AppColors.yandexAmber,
      backgroundColor: AppColors.surface,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Эволюция вкусов',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          Text(
            'Как менялись твои предпочтения по мере добавления треков',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),

          ...segments.map((seg) {
            final isFirst = seg.segmentIndex == 0;
            final isLast = seg.segmentIndex == segments.length - 1;

            return Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: seg.dominantColor.withValues(alpha: 0.4),
                  width: 1.5,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceElevated,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              seg.label,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                          if (isFirst) ...[
                            const SizedBox(width: 8),
                            const Text('🌱 Начало', style: TextStyle(fontSize: 12, color: AppColors.neonGreen)),
                          ] else if (isLast) ...[
                            const SizedBox(width: 8),
                            const Text('🔥 Недавние', style: TextStyle(fontSize: 12, color: AppColors.yandexAmber)),
                          ],
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: seg.dominantColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: seg.dominantColor.withValues(alpha: 0.4)),
                        ),
                        child: Text(
                          seg.dominantGenre,
                          style: TextStyle(
                            color: seg.dominantColor,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // Stacked Segment Bar
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: SizedBox(
                      height: 10,
                      child: Row(
                        children: seg.genres.map((g) {
                          if (g.percent <= 0) return const SizedBox.shrink();
                          return Expanded(
                            flex: (g.percent * 10).toInt(),
                            child: Container(
                              color: g.color,
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Genre chips in this segment
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: seg.genres.map((g) {
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: g.color,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${g.genre}: ${g.percent}%',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontSize: 11,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      );
                    }).toList(),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
