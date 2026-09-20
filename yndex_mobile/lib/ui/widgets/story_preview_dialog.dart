import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import '../../core/theme/app_colors.dart';
import '../../data/models/overview_stats.dart';
import '../../data/models/genre_cluster.dart';
import 'music_story_widget.dart';

class StoryPreviewDialog extends StatefulWidget {
  final OverviewStats stats;
  final List<GenreCluster> clusters;

  const StoryPreviewDialog({
    super.key,
    required this.stats,
    required this.clusters,
  });

  static void show(
    BuildContext context, {
    required OverviewStats stats,
    required List<GenreCluster> clusters,
  }) {
    showDialog(
      context: context,
      builder: (context) => StoryPreviewDialog(stats: stats, clusters: clusters),
    );
  }

  @override
  State<StoryPreviewDialog> createState() => _StoryPreviewDialogState();
}

class _StoryPreviewDialogState extends State<StoryPreviewDialog> {
  final GlobalKey _boundaryKey = GlobalKey();
  bool _isExporting = false;

  Future<void> _exportStory() async {
    setState(() => _isExporting = true);

    try {
      final boundary = _boundaryKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) {
        throw Exception('Не удалось захватить изображение виджета');
      }

      final ui.Image image = await boundary.toImage(pixelRatio: 3.0);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) {
        throw Exception('Не удалось сформировать PNG данные');
      }

      final pngBytes = byteData.buffer.asUint8List();

      if (mounted) {
        setState(() => _isExporting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Story успешно сгенерирована (${pngBytes.lengthInBytes ~/ 1024} КБ)!'),
            backgroundColor: AppColors.neonGreen,
            duration: const Duration(seconds: 4),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isExporting = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ошибка генерации: $e'),
            backgroundColor: AppColors.yandexRed,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Top controls
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Ваша персональная Story (9:16)',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded, color: Colors.white),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Story Card in RepaintBoundary
          Flexible(
            child: SingleChildScrollView(
              child: Center(
                child: RepaintBoundary(
                  key: _boundaryKey,
                  child: MusicStoryWidget(
                    stats: widget.stats,
                    clusters: widget.clusters,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Action Buttons
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _isExporting ? null : _exportStory,
                  icon: _isExporting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                        )
                      : const Icon(Icons.download_rounded),
                  label: Text(_isExporting ? 'Сохранение...' : 'Сохранить Story'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.yandexAmber,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
