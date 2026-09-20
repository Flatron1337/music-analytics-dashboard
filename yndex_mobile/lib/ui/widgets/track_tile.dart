import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_colors.dart';
import '../../data/models/track_item.dart';

class TrackTile extends StatelessWidget {
  final TrackItem track;

  const TrackTile({super.key, required this.track});

  Future<void> _openYandexMusic(BuildContext context) async {
    if (track.yandexUrl.isEmpty) return;
    final uri = Uri.parse(track.yandexUrl);
    try {
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      }
    } catch (_) {
      try {
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      } catch (_) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Не удалось открыть ссылку на трек')),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.cardBorder.withValues(alpha: 0.6)),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: track.genreColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: track.genreColor.withValues(alpha: 0.3)),
            ),
            child: track.coverUri.isNotEmpty
                ? Image.network(
                    track.coverUri,
                    width: 44,
                    height: 44,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) => Center(
                      child: Icon(
                        track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                        color: track.genreColor,
                        size: 22,
                      ),
                    ),
                    loadingBuilder: (context, child, loadingProgress) {
                      if (loadingProgress == null) return child;
                      return Center(
                        child: Icon(
                          track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                          color: track.genreColor.withValues(alpha: 0.6),
                          size: 20,
                        ),
                      );
                    },
                  )
                : Center(
                    child: Icon(
                      track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                      color: track.genreColor,
                      size: 22,
                    ),
                  ),
          ),
        ),
        title: Text(
          track.title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Row(
          children: [
            Expanded(
              child: Text(
                track.artist,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: track.genreColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                track.genre,
                style: TextStyle(
                  color: track.genreColor,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              track.durationFmt,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.textMuted,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: 4),
            IconButton(
              icon: const Icon(Icons.open_in_new_rounded, size: 18, color: AppColors.yandexAmber),
              tooltip: 'Открыть в Яндекс Музыке',
              onPressed: () => _openYandexMusic(context),
            ),
          ],
        ),
      ),
    );
  }
}
