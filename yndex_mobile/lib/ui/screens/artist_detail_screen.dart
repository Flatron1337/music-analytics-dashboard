import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/artist_details.dart';
import '../../data/services/api_service.dart';
import '../widgets/skeleton_loader.dart';
import '../widgets/track_tile.dart';

class ArtistDetailScreen extends StatefulWidget {
  final String artistName;
  final ApiService apiService;

  const ArtistDetailScreen({
    super.key,
    required this.artistName,
    required this.apiService,
  });

  static void navigate(BuildContext context, String artistName, ApiService apiService) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ArtistDetailScreen(
          artistName: artistName,
          apiService: apiService,
        ),
      ),
    );
  }

  @override
  State<ArtistDetailScreen> createState() => _ArtistDetailScreenState();
}

class _ArtistDetailScreenState extends State<ArtistDetailScreen> {
  ArtistDetails? _details;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadArtist();
  }

  Future<void> _loadArtist() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await widget.apiService.fetchArtistDetails(widget.artistName);
      if (mounted) {
        setState(() {
          _details = res;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          if (_details != null && _details!.yandexUrl.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.open_in_new_rounded, color: AppColors.yandexAmber),
              tooltip: 'Открыть в Яндекс Музыке',
              onPressed: () async {
                final uri = Uri.parse(_details!.yandexUrl);
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              },
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const ShimmerLoading(
        child: Padding(
          padding: EdgeInsets.all(20.0),
          child: Column(
            children: [
              Center(child: SkeletonBox(width: 100, height: 100, borderRadius: 50)),
              SizedBox(height: 16),
              SkeletonBox(width: 180, height: 24, borderRadius: 6),
              SizedBox(height: 8),
              SkeletonBox(width: 120, height: 14, borderRadius: 4),
              SizedBox(height: 24),
              SkeletonBox(height: 90, borderRadius: 16),
              SizedBox(height: 12),
              SkeletonBox(height: 90, borderRadius: 16),
            ],
          ),
        ),
      );
    }

    if (_error != null || _details == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.person_off_rounded, size: 64, color: AppColors.textMuted),
              const SizedBox(height: 16),
              Text(
                'Не удалось загрузить артиста',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                _error ?? 'Ошибка связи с сервером',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: _loadArtist,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Повторить'),
              ),
            ],
          ),
        ),
      );
    }

    final d = _details!;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
      children: [
        // Artist Hero Banner
        Center(
          child: Column(
            children: [
              // Avatar
              Container(
                width: 100,
                height: 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      d.dominantColor,
                      d.dominantColor.withValues(alpha: 0.4),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: d.dominantColor.withValues(alpha: 0.3),
                      blurRadius: 24,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Center(
                  child: Text(
                    d.artist.isNotEmpty ? d.artist[0].toUpperCase() : '?',
                    style: const TextStyle(
                      fontSize: 42,
                      fontWeight: FontWeight.w900,
                      color: Colors.black87,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Name
              Text(
                d.artist,
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 6),

              // Rank Badge
              if (d.rank != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: d.rank! <= 3
                        ? AppColors.yandexAmber.withValues(alpha: 0.2)
                        : AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: d.rank! <= 3
                          ? AppColors.yandexAmber.withValues(alpha: 0.6)
                          : AppColors.cardBorder,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        d.rank! <= 3 ? Icons.emoji_events_rounded : Icons.trending_up_rounded,
                        size: 14,
                        color: d.rank! <= 3 ? AppColors.yandexAmber : AppColors.neonGreen,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '#${d.rank} в вашей медиатеке',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: d.rank! <= 3 ? AppColors.yandexAmber : AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // Metrics Grid (2x2)
        Row(
          children: [
            Expanded(
              child: _buildMetricTile(
                icon: Icons.music_note_rounded,
                color: AppColors.yandexAmber,
                label: 'Всего треков',
                value: '${d.totalTracks}',
                subtitle: '${d.librarySharePercent}% всей медиатеки',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricTile(
                icon: Icons.timer_rounded,
                color: AppColors.neonGreen,
                label: 'Хронометраж',
                value: d.totalDurationFmt,
                subtitle: 'в среднем ${d.avgDurationSec ~/ 60}:${(d.avgDurationSec % 60).toString().padLeft(2, "0")}',
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildMetricTile(
                icon: Icons.category_rounded,
                color: d.dominantColor,
                label: 'Главный жанр',
                value: d.dominantGenre,
                subtitle: '${d.genres.isNotEmpty ? d.genres.first.percent : 0}% звучания',
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildMetricTile(
                icon: Icons.people_alt_rounded,
                color: AppColors.neonPurple,
                label: 'Формат',
                value: '${d.soloCount} соло',
                subtitle: '${d.collabCount} совместных фитов',
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),

        // Collaborators Section (if any)
        if (d.topCollaborators.isNotEmpty) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'С кем записывал треки',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
              Text(
                '${d.topCollaborators.length} артистов',
                style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: d.topCollaborators.map((collab) {
                return Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: () {
                      ArtistDetailScreen.navigate(context, collab.artist, widget.apiService);
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppColors.cardBorder),
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 12,
                            backgroundColor: AppColors.neonPurple.withValues(alpha: 0.2),
                            child: Text(
                              collab.artist.isNotEmpty ? collab.artist[0].toUpperCase() : '?',
                              style: const TextStyle(fontSize: 10, color: AppColors.neonPurple, fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                collab.artist,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
                              ),
                              Text(
                                '${collab.count} ${collab.count == 1 ? "фит" : "фита"}',
                                style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
                              ),
                            ],
                          ),
                          const SizedBox(width: 4),
                          const Icon(Icons.arrow_forward_ios_rounded, size: 10, color: AppColors.textMuted),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 24),
        ],

        // Tracks Section
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Треки в коллекции',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            Text(
              '${d.tracks.length} шт.',
              style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
          ],
        ),
        const SizedBox(height: 8),

        ...d.tracks.map((t) => TrackTile(track: t)),

        const SizedBox(height: 24),

        // Open in Yandex Button
        if (d.yandexUrl.isNotEmpty)
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () async {
                final uri = Uri.parse(d.yandexUrl);
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              },
              icon: const Icon(Icons.open_in_browser_rounded),
              label: Text('Открыть ${d.artist} в Яндекс Музыке'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.yandexAmber,
                foregroundColor: Colors.black,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildMetricTile({
    required IconData icon,
    required Color color,
    required String label,
    required String value,
    required String subtitle,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.cardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Colors.white),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: const TextStyle(fontSize: 10, color: AppColors.textSecondary),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
