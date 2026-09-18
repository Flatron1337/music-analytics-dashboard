import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/formatters.dart';
import '../../data/models/genre_cluster.dart';
import '../../state/app_view_model.dart';
import '../widgets/genre_pie_chart.dart';

class GenresTab extends StatelessWidget {
  final AppViewModel viewModel;

  const GenresTab({super.key, required this.viewModel});

  void _filterByGenre(BuildContext context, GenreCluster cluster) {
    viewModel.setGenreFilter(cluster.name);
    viewModel.setTab(3); // Switch to Tracks tab
  }

  @override
  Widget build(BuildContext context) {
    if (viewModel.isLoadingGenres) {
      return const Center(child: CircularProgressIndicator());
    }

    final clusters = viewModel.genres;
    if (clusters.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.pie_chart_outline_rounded, size: 64, color: AppColors.textMuted),
            const SizedBox(height: 16),
            const Text('Нет данных о жанрах'),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: () => viewModel.loadGenres(forceRefresh: true),
              child: const Text('Загрузить'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => viewModel.loadGenres(forceRefresh: true),
      color: AppColors.yandexAmber,
      backgroundColor: AppColors.surface,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Жанровые Кластеры',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          Text(
            'Кластеризация треков по музыкальным стилям',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),

          // Donut Chart Card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.cardBorder),
            ),
            child: Column(
              children: [
                GenrePieChart(
                  clusters: clusters,
                  onSelectCluster: (cluster) {
                    if (cluster != null) {
                      // Optionally update something
                    }
                  },
                ),
                const SizedBox(height: 12),
                Text(
                  'Нажмите на сектор диаграммы для деталей',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          Text(
            'Распределение по кластерам',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),

          // Grid / List of cluster cards
          ...clusters.map((cluster) {
            return Container(
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: cluster.color.withValues(alpha: 0.3)),
              ),
              child: Material(
                color: Colors.transparent,
                borderRadius: BorderRadius.circular(16),
                child: InkWell(
                  borderRadius: BorderRadius.circular(16),
                  onTap: () => _filterByGenre(context, cluster),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: cluster.color.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(cluster.icon, color: cluster.color, size: 24),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    cluster.name,
                                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${Formatters.formatNumber(cluster.count)} треков',
                                    style: Theme.of(context).textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(
                                  '${cluster.percent}%',
                                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                    color: cluster.color,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      'Открыть',
                                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                        color: AppColors.textMuted,
                                      ),
                                    ),
                                    const Icon(Icons.chevron_right_rounded, size: 14, color: AppColors.textMuted),
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: cluster.percent / 100.0,
                            minHeight: 6,
                            backgroundColor: AppColors.surfaceElevated,
                            valueColor: AlwaysStoppedAnimation(cluster.color),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
