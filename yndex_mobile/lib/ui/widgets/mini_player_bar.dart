import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../data/services/audio_player_service.dart';

class MiniPlayerBar extends StatelessWidget {
  const MiniPlayerBar({super.key});

  @override
  Widget build(BuildContext context) {
    final playerService = AudioPlayerService();

    return ListenableBuilder(
      listenable: playerService,
      builder: (context, _) {
        final trackId = playerService.currentTrackId;
        if (trackId == null) {
          return const SizedBox.shrink();
        }

        final title = playerService.currentTitle ?? 'Без названия';
        final artist = playerService.currentArtist ?? 'Неизвестный исполнитель';
        final coverUrl = playerService.currentCoverUrl;
        final isPlaying = playerService.isPlaying;
        final isLoading = playerService.isLoading;
        final position = playerService.position;
        final duration = playerService.duration;

        double progress = 0.0;
        if (duration.inMilliseconds > 0) {
          progress = (position.inMilliseconds / duration.inMilliseconds).clamp(0.0, 1.0);
        }

        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF141923).withValues(alpha: 0.95),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: AppColors.cyanAccent.withValues(alpha: 0.3),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
              BoxShadow(
                color: AppColors.cyanAccent.withValues(alpha: 0.15),
                blurRadius: 12,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Row(
                  children: [
                    // Cover
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Container(
                        width: 44,
                        height: 44,
                        color: Colors.white10,
                        child: coverUrl != null && coverUrl.isNotEmpty
                            ? Image.network(
                                coverUrl,
                                fit: BoxFit.cover,
                                errorBuilder: (context, error, stackTrace) => const Icon(
                                  Icons.music_note,
                                  color: AppColors.cyanAccent,
                                  size: 22,
                                ),
                              )
                            : const Icon(
                                Icons.music_note,
                                color: AppColors.cyanAccent,
                                size: 22,
                              ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Title and Artist
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            artist,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Play/Pause button
                    IconButton(
                      iconSize: 28,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
                      icon: isLoading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation(AppColors.cyanAccent),
                              ),
                            )
                          : Icon(
                              isPlaying ? Icons.pause_circle_filled : Icons.play_circle_filled,
                              color: AppColors.cyanAccent,
                            ),
                      onPressed: () => playerService.togglePlayPause(),
                    ),
                    // Close button
                    IconButton(
                      iconSize: 20,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                      icon: const Icon(
                        Icons.close,
                        color: AppColors.textTertiary,
                      ),
                      onPressed: () => playerService.stop(),
                    ),
                  ],
                ),
              ),
              // Mini progress line
              ClipRRect(
                borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16)),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 2.5,
                  backgroundColor: Colors.white12,
                  valueColor: const AlwaysStoppedAnimation(AppColors.cyanAccent),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
