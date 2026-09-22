import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme/app_colors.dart';
import '../../data/models/track_item.dart';
import '../../data/services/api_service.dart';
import '../../data/services/audio_player_service.dart';
import '../screens/artist_detail_screen.dart';

class TrackTile extends StatefulWidget {
  final TrackItem track;
  final ApiService? apiService;

  const TrackTile({super.key, required this.track, this.apiService});

  @override
  State<TrackTile> createState() => _TrackTileState();
}

class _TrackTileState extends State<TrackTile> {
  bool _isLoadingStream = false;

  Future<void> _openYandexMusic(BuildContext context) async {
    if (widget.track.yandexUrl.isEmpty) return;
    final uri = Uri.parse(widget.track.yandexUrl);
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

  Future<void> _handlePlayPreview() async {
    final playerService = AudioPlayerService();
    final trackId = widget.track.id.toString();

    if (playerService.isTrackActive(trackId)) {
      await playerService.togglePlayPause();
      return;
    }

    if (widget.apiService == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Сервис воспроизведения недоступен')),
        );
      }
      return;
    }

    setState(() => _isLoadingStream = true);
    try {
      final streamUrl = await widget.apiService!.fetchTrackStream(
        trackId,
        title: widget.track.title,
        artist: widget.track.artist,
      );
      if (streamUrl != null && streamUrl.isNotEmpty) {
        await playerService.playTrack(
          trackId: trackId,
          title: widget.track.title,
          artist: widget.track.artist,
          coverUrl: widget.track.coverUri.isNotEmpty ? widget.track.coverUri : null,
          streamUrl: streamUrl,
        );
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Не удалось получить поток для прослушивания')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка стриминга: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoadingStream = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final playerService = AudioPlayerService();

    return ListenableBuilder(
      listenable: playerService,
      builder: (context, _) {
        final trackId = widget.track.id.toString();
        final isPlaying = playerService.isTrackPlaying(trackId);
        final isActive = playerService.isTrackActive(trackId);

        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          decoration: BoxDecoration(
            color: isActive ? AppColors.surfaceElevated : AppColors.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isActive
                  ? AppColors.cyanAccent.withValues(alpha: 0.5)
                  : AppColors.cardBorder.withValues(alpha: 0.6),
              width: isActive ? 1.4 : 1.0,
            ),
          ),
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            onTap: () {
              if (widget.apiService != null) {
                ArtistDetailScreen.navigate(context, widget.track.artist, widget.apiService!);
              } else {
                _openYandexMusic(context);
              }
            },
            leading: Stack(
              alignment: Alignment.center,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: widget.track.genreColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: widget.track.genreColor.withValues(alpha: 0.3)),
                    ),
                    child: widget.track.coverUri.isNotEmpty
                        ? Image.network(
                            widget.track.coverUri,
                            width: 44,
                            height: 44,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => Center(
                              child: Icon(
                                widget.track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                                color: widget.track.genreColor,
                                size: 22,
                              ),
                            ),
                            loadingBuilder: (context, child, loadingProgress) {
                              if (loadingProgress == null) return child;
                              return Center(
                                child: Icon(
                                  widget.track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                                  color: widget.track.genreColor.withValues(alpha: 0.6),
                                  size: 20,
                                ),
                              );
                            },
                          )
                        : Center(
                            child: Icon(
                              widget.track.isCollab ? Icons.group_rounded : Icons.music_note_rounded,
                              color: widget.track.genreColor,
                              size: 22,
                            ),
                          ),
                  ),
                ),
                // Play overlay if active
                if (isActive)
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.55),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(
                      isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                      color: AppColors.cyanAccent,
                      size: 26,
                    ),
                  ),
              ],
            ),
            title: Text(
              widget.track.title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: isActive ? AppColors.cyanAccent : AppColors.textPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Row(
              children: [
                Expanded(
                  child: Text(
                    widget.track.artist,
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
                    color: widget.track.genreColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    widget.track.genre,
                    style: TextStyle(
                      color: widget.track.genreColor,
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
                // Play preview icon button
                IconButton(
                  iconSize: 22,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  icon: _isLoadingStream
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill_rounded,
                          color: isActive ? AppColors.cyanAccent : AppColors.textSecondary,
                        ),
                  tooltip: 'Слушать превью',
                  onPressed: _handlePlayPreview,
                ),
                const SizedBox(width: 4),
                Text(
                  widget.track.durationFmt,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textMuted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 2),
                IconButton(
                  icon: const Icon(Icons.open_in_new_rounded, size: 18, color: AppColors.yandexAmber),
                  tooltip: 'Открыть в Яндекс Музыке',
                  onPressed: () => _openYandexMusic(context),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
