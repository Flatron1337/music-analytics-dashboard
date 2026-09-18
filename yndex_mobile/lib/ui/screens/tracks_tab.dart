import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../core/utils/formatters.dart';
import '../../state/app_view_model.dart';
import '../widgets/track_tile.dart';

class TracksTab extends StatefulWidget {
  final AppViewModel viewModel;

  const TracksTab({super.key, required this.viewModel});

  @override
  State<TracksTab> createState() => _TracksTabState();
}

class _TracksTabState extends State<TracksTab> {
  final TextEditingController _searchController = TextEditingController();

  final List<String> _genreFilters = [
    'Все',
    'Dubstep & EDM',
    'Heavy & Metal',
    'Phonk & Memphis',
    'Hip-Hop & Trap',
    'Rock & Alternative',
    'Other & Electronic',
  ];

  @override
  void initState() {
    super.initState();
    _searchController.text = widget.viewModel.searchQuery;
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final vm = widget.viewModel;

    return Column(
      children: [
        // Search & Filter Header
        Container(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          color: AppColors.background,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Каталог треков',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),

              // Search Bar
              TextField(
                controller: _searchController,
                onChanged: (val) => vm.setSearchQuery(val),
                decoration: InputDecoration(
                  hintText: 'Поиск по названию или артисту...',
                  prefixIcon: const Icon(Icons.search_rounded, color: AppColors.textSecondary),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear_rounded, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            vm.setSearchQuery('');
                          },
                        )
                      : null,
                ),
              ),
              const SizedBox(height: 12),

              // Genre Filter Chips
              SizedBox(
                height: 36,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: _genreFilters.length,
                  separatorBuilder: (context, index) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final genre = _genreFilters[index];
                    final isSelected = vm.selectedGenreFilter == genre;
                    final chipColor = genre == 'Все' ? AppColors.yandexAmber : AppColors.getClusterColor(genre);

                    return FilterChip(
                      label: Text(genre),
                      selected: isSelected,
                      onSelected: (_) => vm.setGenreFilter(genre),
                      backgroundColor: AppColors.surface,
                      selectedColor: chipColor.withValues(alpha: 0.25),
                      checkmarkColor: chipColor,
                      labelStyle: TextStyle(
                        color: isSelected ? chipColor : AppColors.textSecondary,
                        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        fontSize: 12,
                      ),
                      side: BorderSide(
                        color: isSelected ? chipColor : AppColors.cardBorder,
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 8),

              // Stats counter
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Найдено: ${Formatters.formatNumber(vm.totalTracksFound)} треков',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  if (vm.tracksTotalPages > 1)
                    Text(
                      'Стр. ${vm.tracksPage} из ${vm.tracksTotalPages}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textMuted,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),

        // Track List
        Expanded(
          child: vm.isLoadingTracks
              ? const Center(child: CircularProgressIndicator())
              : vm.tracks.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.music_off_rounded, size: 48, color: AppColors.textMuted),
                          const SizedBox(height: 12),
                          Text(
                            'Треки не найдены',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Попробуйте изменить поисковый запрос или фильтр жанров',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      itemCount: vm.tracks.length,
                      itemBuilder: (context, index) {
                        final track = vm.tracks[index];
                        return TrackTile(track: track);
                      },
                    ),
        ),

        // Pagination Bar
        if (vm.tracksTotalPages > 1)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              border: Border(top: BorderSide(color: AppColors.cardBorder)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton.filledTonal(
                  icon: const Icon(Icons.arrow_back_ios_rounded, size: 16),
                  onPressed: vm.tracksPage > 1 ? vm.prevPage : null,
                ),
                Text(
                  'Страница ${vm.tracksPage} / ${vm.tracksTotalPages}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                IconButton.filledTonal(
                  icon: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
                  onPressed: vm.tracksPage < vm.tracksTotalPages ? vm.nextPage : null,
                ),
              ],
            ),
          ),
      ],
    );
  }
}
