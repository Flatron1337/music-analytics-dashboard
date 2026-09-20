import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/formatters.dart';
import '../../state/app_view_model.dart';
import '../widgets/metric_card.dart';
import '../widgets/skeleton_loader.dart';

class OverviewTab extends StatelessWidget {
  final AppViewModel viewModel;

  const OverviewTab({super.key, required this.viewModel});

  @override
  Widget build(BuildContext context) {
    if (viewModel.isLoadingOverview && viewModel.overviewStats == null) {
      return const OverviewSkeleton();
    }

    final stats = viewModel.overviewStats;
    if (stats == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 64, color: AppColors.textMuted),
              const SizedBox(height: 16),
              Text(
                'Бэкенд недоступен',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                viewModel.overviewError ?? 'Проверьте, запущен ли сервер python api.py',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: () => viewModel.loadOverview(forceRefresh: true),
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Повторить попытку'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => viewModel.loadDashboardData(forceRefresh: true),
      color: AppColors.yandexAmber,
      backgroundColor: AppColors.surface,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Музыкальный обзор',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  Text(
                    'Аналитика твоей медиатеки',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.neonGreen.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.neonGreen.withValues(alpha: 0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.circle, size: 8, color: AppColors.neonGreen),
                    const SizedBox(width: 6),
                    Text(
                      'Live API',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.neonGreen,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Primary 2x2 Grid
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.25,
            children: [
              MetricCard(
                title: 'Всего треков',
                value: Formatters.formatNumber(stats.totalTracks),
                icon: Icons.library_music_rounded,
                accentColor: AppColors.yandexAmber,
              ),
              MetricCard(
                title: 'Артистов',
                value: Formatters.formatNumber(stats.uniqueArtists),
                icon: Icons.person_rounded,
                accentColor: AppColors.neonPurple,
              ),
              MetricCard(
                title: 'Время музыки',
                value: stats.totalDurationFmt,
                icon: Icons.access_time_rounded,
                accentColor: AppColors.neonCyan,
              ),
              MetricCard(
                title: 'Средняя длина',
                value: stats.avgDurationFmt,
                subtitle: '${stats.avgDurationSec} сек. / трек',
                icon: Icons.timelapse_rounded,
                accentColor: AppColors.neonGreen,
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Solo vs Collab Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.cardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Соло vs Коллаборации',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Text(
                      '${stats.collabRatioPercent}% фитов',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.yandexAmber,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: stats.collabRatioPercent / 100.0,
                    minHeight: 12,
                    backgroundColor: AppColors.neonCyan.withValues(alpha: 0.3),
                    valueColor: const AlwaysStoppedAnimation(AppColors.yandexAmber),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.person, size: 16, color: AppColors.neonCyan),
                        const SizedBox(width: 6),
                        Text(
                          'Соло: ${Formatters.formatNumber(stats.soloCount)}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        const Icon(Icons.group, size: 16, color: AppColors.yandexAmber),
                        const SizedBox(width: 6),
                        Text(
                          'Коллабы: ${Formatters.formatNumber(stats.collabCount)}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Top Artists List
          Text(
            'Топ-15 Артистов медиатеки',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: stats.topArtists.length,
            itemBuilder: (context, index) {
              final artist = stats.topArtists[index];
              final maxCount = stats.topArtists.isNotEmpty ? stats.topArtists.first.count : 1;
              final ratio = artist.count / maxCount;

              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.cardBorder.withValues(alpha: 0.5)),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: index < 3
                                ? AppColors.yandexAmber.withValues(alpha: 0.2)
                                : AppColors.surfaceElevated,
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: Text(
                              '${index + 1}',
                              style: TextStyle(
                                color: index < 3 ? AppColors.yandexAmber : AppColors.textSecondary,
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            artist.artist,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          '${artist.count} треков',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.yandexAmber,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: ratio,
                        minHeight: 4,
                        backgroundColor: AppColors.surfaceElevated,
                        valueColor: AlwaysStoppedAnimation(
                          index < 3 ? AppColors.yandexAmber : AppColors.neonPurple,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
