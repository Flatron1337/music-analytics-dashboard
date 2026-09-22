import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_colors.dart';
import '../../data/models/duplicates_data.dart';
import '../../data/services/api_service.dart';
import '../../data/services/audio_player_service.dart';

class DuplicatesScreen extends StatefulWidget {
  final ApiService apiService;

  const DuplicatesScreen({super.key, required this.apiService});

  static void navigate(BuildContext context, ApiService apiService) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DuplicatesScreen(apiService: apiService),
      ),
    );
  }

  @override
  State<DuplicatesScreen> createState() => _DuplicatesScreenState();
}

class _DuplicatesScreenState extends State<DuplicatesScreen> {
  late Future<DuplicatesData> _duplicatesFuture;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _duplicatesFuture = widget.apiService.fetchDuplicates();
  }

  Future<void> _refresh() async {
    setState(() {
      _duplicatesFuture = widget.apiService.fetchDuplicates();
    });
  }

  Future<void> _openYandexMusic(String? url) async {
    if (url == null || url.isEmpty) return;
    final uri = Uri.parse(url);
    try {
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text(
          '🔍 Поиск дубликатов треков',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'Обновить',
            onPressed: _refresh,
          ),
        ],
      ),
      body: FutureBuilder<DuplicatesData>(
        future: _duplicatesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation(AppColors.cyanAccent),
              ),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 48),
                    const SizedBox(height: 12),
                    Text(
                      'Ошибка: ${snapshot.error}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _refresh,
                      child: const Text('Повторить'),
                    ),
                  ],
                ),
              ),
            );
          }

          final data = snapshot.data;
          if (data == null || data.groups.isEmpty) {
            return const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.check_circle_outline_rounded, color: AppColors.neonGreen, size: 56),
                  SizedBox(height: 16),
                  Text(
                    'Поздравляем! Дубликатов не найдено.',
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            );
          }

          final filteredGroups = _searchQuery.isEmpty
              ? data.groups
              : data.groups.where((g) {
                  final q = _searchQuery.toLowerCase();
                  return g.artist.toLowerCase().contains(q) ||
                      g.title.toLowerCase().contains(q);
                }).toList();

          return CustomScrollView(
            slivers: [
              // Summary Header Cards
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      // Banner
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF1E1B4B), Color(0xFF311042)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: AppColors.phonkPurple.withValues(alpha: 0.4),
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: AppColors.phonkPurple.withValues(alpha: 0.2),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.auto_awesome_motion_rounded,
                                color: AppColors.phonkPurple,
                                size: 28,
                              ),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Найдено ${data.totalDuplicates} дубликатов',
                                    style: const TextStyle(
                                      color: AppColors.textPrimary,
                                      fontWeight: FontWeight.w800,
                                      fontSize: 16,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'В ${data.duplicateGroupsCount} группах • Лишнее время: ${data.totalRedundantTimeFmt}',
                                    style: const TextStyle(
                                      color: AppColors.textSecondary,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Search input
                      TextField(
                        style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
                        decoration: InputDecoration(
                          hintText: 'Поиск по артисту или названию...',
                          hintStyle: const TextStyle(color: AppColors.textMuted),
                          prefixIcon: const Icon(Icons.search_rounded, color: AppColors.textMuted),
                          filled: true,
                          fillColor: AppColors.surface,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        ),
                        onChanged: (val) => setState(() => _searchQuery = val.trim()),
                      ),
                    ],
                  ),
                ),
              ),

              // Duplicate Groups List
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final group = filteredGroups[index];
                    return _buildGroupCard(group);
                  },
                  childCount: filteredGroups.length,
                ),
              ),
              const SliverToBoxAdapter(child: SizedBox(height: 32)),
            ],
          );
        },
      ),
    );
  }

  Widget _buildGroupCard(DuplicateGroup group) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.cardBorder.withValues(alpha: 0.6)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Group Header
          Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        group.artist,
                        style: const TextStyle(
                          color: AppColors.cyanAccent,
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        group.title,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w600,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.white10,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${group.count} версий',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 1, color: Colors.white12),
          // Tracks
          ...group.tracks.map((track) => _buildTrackRow(track)),
        ],
      ),
    );
  }

  Widget _buildTrackRow(DuplicateTrackItem track) {
    final playerService = AudioPlayerService();

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          // Badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
            decoration: BoxDecoration(
              color: track.isOriginal
                  ? AppColors.neonGreen.withValues(alpha: 0.15)
                  : Colors.orange.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: track.isOriginal
                    ? AppColors.neonGreen.withValues(alpha: 0.4)
                    : Colors.orange.withValues(alpha: 0.4),
              ),
            ),
            child: Text(
              track.isOriginal ? 'Оригинал' : 'Дубликат',
              style: TextStyle(
                color: track.isOriginal ? AppColors.neonGreen : Colors.orange,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Cover
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Container(
              width: 32,
              height: 32,
              color: Colors.white10,
              child: track.coverUrl != null
                  ? Image.network(
                      track.coverUrl!,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) => const Icon(Icons.music_note, size: 16),
                    )
                  : const Icon(Icons.music_note, size: 16),
            ),
          ),
          const SizedBox(width: 10),
          // Title
          Expanded(
            child: Text(
              track.title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: track.isOriginal ? AppColors.textPrimary : AppColors.textSecondary,
                fontSize: 12,
                fontWeight: track.isOriginal ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
          const SizedBox(width: 8),
          // Duration
          Text(
            track.durationFmt,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          // Listen preview button
          IconButton(
            iconSize: 20,
            constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
            padding: EdgeInsets.zero,
            icon: const Icon(Icons.play_circle_outline_rounded, color: AppColors.cyanAccent),
            tooltip: 'Слушать превью',
            onPressed: () async {
              final streamUrl = await widget.apiService.fetchTrackStream(track.id);
              if (streamUrl != null) {
                await playerService.playTrack(
                  trackId: track.id,
                  title: track.title,
                  artist: track.artist,
                  coverUrl: track.coverUrl,
                  streamUrl: streamUrl,
                );
              }
            },
          ),
          // Open in Yandex button
          IconButton(
            iconSize: 18,
            constraints: const BoxConstraints(minWidth: 28, minHeight: 28),
            padding: EdgeInsets.zero,
            icon: const Icon(Icons.open_in_new_rounded, color: AppColors.yandexAmber),
            tooltip: 'Открыть в Яндекс Музыке',
            onPressed: () => _openYandexMusic(track.yandexUrl),
          ),
        ],
      ),
    );
  }
}
