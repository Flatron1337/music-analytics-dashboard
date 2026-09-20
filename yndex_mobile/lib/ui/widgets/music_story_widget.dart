import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../data/models/overview_stats.dart';
import '../../data/models/genre_cluster.dart';

class MusicStoryWidget extends StatelessWidget {
  final OverviewStats stats;
  final List<GenreCluster> clusters;

  const MusicStoryWidget({
    super.key,
    required this.stats,
    required this.clusters,
  });

  Map<String, String> _getArchetype() {
    final topGenre = clusters.isNotEmpty ? clusters.first.name.toLowerCase() : '';
    if (topGenre.contains('dubstep') || topGenre.contains('edm')) {
      return {
        'title': '⚡ Электронный Рейвер',
        'desc': 'Максимальная энергия, дропы и мощные басы',
        'color': '#00E5FF',
      };
    } else if (topGenre.contains('metal') || topGenre.contains('heavy')) {
      return {
        'title': '🔥 Неукротимый Металхэд',
        'desc': 'Перегруженные риффы и бескомпромиссный драйв',
        'color': '#FF3D00',
      };
    } else if (topGenre.contains('phonk') || topGenre.contains('memphis')) {
      return {
        'title': '🏎️ Ночной Дрифтер',
        'desc': 'Атмосфера ночного города, 808-й бас и дрифт-вайб',
        'color': '#D500F9',
      };
    } else if (topGenre.contains('hip-hop') || topGenre.contains('trap')) {
      return {
        'title': '🎤 Трэп-Коннектор',
        'desc': 'Стильный флоу, плотные биты и сочные коллаборации',
        'color': '#FFD600',
      };
    } else if (topGenre.contains('rock')) {
      return {
        'title': '🎸 Рок-Эстет',
        'desc': 'Живой звук, глубокая мелодика и классика жанра',
        'color': '#00E676',
      };
    } else {
      return {
        'title': '🌌 Музыкальный Исследователь',
        'desc': 'Разносторонний вкус без строгих жанровых границ',
        'color': '#FFCC00',
      };
    }
  }

  @override
  Widget build(BuildContext context) {
    final archetype = _getArchetype();
    final topArtists = stats.topArtists.take(3).toList();

    return Container(
      width: 360,
      height: 640,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const RadialGradient(
          center: Alignment(0.4, -0.6),
          radius: 1.2,
          colors: [
            Color(0xFF2C1548),
            Color(0xFF13111C),
            Color(0xFF0A090F),
          ],
        ),
        boxShadow: const [
          BoxShadow(
            color: Colors.black87,
            blurRadius: 30,
            spreadRadius: 5,
          ),
        ],
      ),
      child: Stack(
        children: [
          // Background Glow Accents
          Positioned(
            top: -40,
            right: -40,
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.neonPurple.withValues(alpha: 0.18),
              ),
            ),
          ),
          Positioned(
            bottom: -60,
            left: -40,
            child: Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.yandexAmber.withValues(alpha: 0.12),
              ),
            ),
          ),

          // Foreground Content
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 26),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Header
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: AppColors.yandexAmber,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Icon(Icons.music_note_rounded, size: 16, color: Colors.black),
                        ),
                        const SizedBox(width: 8),
                        const Text(
                          'Яндекс Музыка',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                      ),
                      child: const Text(
                        'MY MUSIC STORY',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: AppColors.yandexAmber,
                          letterSpacing: 1.2,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 28),

                // Archetype Section
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'ВАШ МУЗЫКАЛЬНЫЙ АРХЕТИП',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textMuted,
                          letterSpacing: 1.5,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        archetype['title']!,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        archetype['desc']!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),

                // 3 Key Stats
                Row(
                  children: [
                    Expanded(
                      child: _buildStoryStat(
                        label: 'Хронометраж',
                        val: stats.totalDurationFmt,
                        icon: Icons.timer_rounded,
                        color: AppColors.neonGreen,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _buildStoryStat(
                        label: 'Любимых треков',
                        val: '${stats.totalTracks}',
                        icon: Icons.favorite_rounded,
                        color: AppColors.yandexRed,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _buildStoryStat(
                        label: 'Коллаборации',
                        val: '${stats.collabRatioPercent}%',
                        icon: Icons.people_rounded,
                        color: AppColors.neonPurple,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),

                // Top-3 Artists Podium
                const Text(
                  'ГЛАВНЫЕ АРТИСТЫ МЕДИАТЕКИ',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: AppColors.textMuted,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 10),

                for (int i = 0; i < topArtists.length; i++) ...[
                  Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.04),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: i == 0
                            ? AppColors.yandexAmber.withValues(alpha: 0.6)
                            : Colors.white.withValues(alpha: 0.08),
                      ),
                    ),
                    child: Row(
                      children: [
                        Text(
                          i == 0 ? '🥇' : i == 1 ? '🥈' : '🥉',
                          style: const TextStyle(fontSize: 18),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            topArtists[i].artist,
                            style: const TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          '${topArtists[i].count} треков',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: i == 0 ? AppColors.yandexAmber : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const Spacer(),

                // Dominant Genres Tags
                if (clusters.isNotEmpty) ...[
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: clusters.take(4).map((c) {
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: c.color.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: c.color.withValues(alpha: 0.3)),
                        ),
                        child: Text(
                          '${c.name} • ${c.percent}%',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: c.color,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 14),
                ],

                // Footer
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text(
                      'Music Analytics Dashboard',
                      style: TextStyle(fontSize: 11, color: AppColors.textMuted),
                    ),
                    Text(
                      'ya.ru/music',
                      style: TextStyle(fontSize: 11, color: AppColors.yandexAmber, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStoryStat({
    required String label,
    required String val,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(height: 6),
          Text(
            val,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
