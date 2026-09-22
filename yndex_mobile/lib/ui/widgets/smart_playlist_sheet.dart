import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_colors.dart';
import '../../state/app_view_model.dart';
import '../../state/yandex_auth_view_model.dart';

class SmartPlaylistSheet extends StatefulWidget {
  final AppViewModel appViewModel;
  final YandexAuthViewModel authViewModel;
  final String? initialPreset;
  final String? initialGenre;

  const SmartPlaylistSheet({
    super.key,
    required this.appViewModel,
    required this.authViewModel,
    this.initialPreset,
    this.initialGenre,
  });

  static Future<void> show(
    BuildContext context, {
    required AppViewModel appViewModel,
    required YandexAuthViewModel authViewModel,
    String? initialPreset,
    String? initialGenre,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SmartPlaylistSheet(
        appViewModel: appViewModel,
        authViewModel: authViewModel,
        initialPreset: initialPreset,
        initialGenre: initialGenre,
      ),
    );
  }

  @override
  State<SmartPlaylistSheet> createState() => _SmartPlaylistSheetState();
}

class _SmartPlaylistSheetState extends State<SmartPlaylistSheet> {
  late String _selectedPreset;
  late String _selectedGenre;
  int _limit = 100;
  final TextEditingController _titleController = TextEditingController();

  bool _isSuccess = false;
  String? _createdTitle;
  String? _createdUrl;
  int _createdCount = 0;
  String? _errorMessage;

  final List<Map<String, dynamic>> _presets = [
    {
      'id': 'genre',
      'title': 'Жанровый микс',
      'desc': 'Треки одного жанрового кластера',
      'icon': Icons.bolt_rounded,
      'color': AppColors.yandexAmber,
      'defaultTitle': '⚡ Жанровый микс',
    },
    {
      'id': 'collab',
      'title': 'Фитотека',
      'desc': 'Только совместные треки артистов',
      'icon': Icons.people_alt_rounded,
      'color': AppColors.neonPurple,
      'defaultTitle': '🤝 Фитотека — Все фиты',
    },
    {
      'id': 'gems',
      'title': 'Скрытые жемчужины',
      'desc': 'Редкие исполнители (1–2 трека)',
      'icon': Icons.diamond_rounded,
      'color': AppColors.cyberCyan,
      'defaultTitle': '💎 Скрытые жемчужины',
    },
    {
      'id': 'golden_era',
      'title': 'Золотая эра',
      'desc': 'Самые первые добавленные лайки',
      'icon': Icons.history_rounded,
      'color': AppColors.neonGreen,
      'defaultTitle': '⏳ Золотая эра — Первые лайки',
    },
    {
      'id': 'solo',
      'title': 'Соло вокал',
      'desc': 'Только сольные треки без фитов',
      'icon': Icons.mic_rounded,
      'color': AppColors.yandexRed,
      'defaultTitle': '🎙️ Соло вокал',
    },
  ];

  @override
  void initState() {
    super.initState();
    _selectedPreset = widget.initialPreset ?? 'genre';

    // Pick first available genre or default
    final clusters = widget.appViewModel.genres;
    if (widget.initialGenre != null && widget.initialGenre!.isNotEmpty) {
      _selectedGenre = widget.initialGenre!;
    } else if (clusters.isNotEmpty) {
      _selectedGenre = clusters.first.name;
    } else {
      _selectedGenre = 'Phonk & Memphis';
    }

    _updateDefaultTitle();
  }

  void _updateDefaultTitle() {
    final presetObj = _presets.firstWhere(
      (p) => p['id'] == _selectedPreset,
      orElse: () => _presets.first,
    );

    if (_selectedPreset == 'genre') {
      _titleController.text = '⚡ $_selectedGenre — Подборка';
    } else {
      _titleController.text = presetObj['defaultTitle'] as String;
    }
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  Future<void> _export() async {
    setState(() {
      _errorMessage = null;
      _isSuccess = false;
    });

    try {
      final res = await widget.authViewModel.exportPlaylist(
        preset: _selectedPreset,
        genre: _selectedPreset == 'genre' ? _selectedGenre : null,
        title: _titleController.text.trim(),
        limit: _limit,
      );

      if (res != null && res['success'] == true) {
        setState(() {
          _isSuccess = true;
          _createdTitle = res['playlist_title'] as String?;
          _createdUrl = res['playlist_url'] as String?;
          _createdCount = (res['tracks_count'] as num?)?.toInt() ?? 0;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        top: 20,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: const BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.cardBorder,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Title
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Умный плейлист',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Экспорт подборки прямо в Яндекс Музыку',
                      style: TextStyle(fontSize: 12, color: AppColors.textMuted),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: AppColors.textMuted),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 18),

            if (_isSuccess) ...[
              // Success Screen
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.neonGreen.withValues(alpha: 0.5)),
                ),
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.neonGreen.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.check_circle_rounded, color: AppColors.neonGreen, size: 48),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Плейлист успешно создан!',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.neonGreen,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '«${_createdTitle ?? "Плейлист"}»',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Добавлено $_createdCount треков в ваш аккаунт',
                      style: const TextStyle(fontSize: 13, color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 20),
                    if (_createdUrl != null) ...[
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton.icon(
                              onPressed: () async {
                                final uri = Uri.parse(_createdUrl!);
                                await launchUrl(uri, mode: LaunchMode.externalApplication);
                              },
                              icon: const Icon(Icons.open_in_browser_rounded),
                              label: const Text('Открыть в Яндекс Музыке'),
                              style: FilledButton.styleFrom(
                                backgroundColor: AppColors.yandexAmber,
                                foregroundColor: Colors.black,
                                padding: const EdgeInsets.symmetric(vertical: 14),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          IconButton.filledTonal(
                            icon: const Icon(Icons.copy_rounded),
                            tooltip: 'Скопировать ссылку',
                            onPressed: () {
                              Clipboard.setData(ClipboardData(text: _createdUrl!));
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Ссылка на плейлист скопирована!')),
                              );
                            },
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () {
                    setState(() {
                      _isSuccess = false;
                    });
                  },
                  child: const Text('Создать ещё один плейлист'),
                ),
              ),
            ] else ...[
              // Configuration Form

              // 1. Preset Selector
              const Text(
                'Выберите алгоритм подборки:',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 10),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: _presets.map((p) {
                    final isSelected = _selectedPreset == p['id'];
                    final color = p['color'] as Color;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        selected: isSelected,
                        onSelected: (val) {
                          if (val) {
                            setState(() {
                              _selectedPreset = p['id'] as String;
                              _updateDefaultTitle();
                            });
                          }
                        },
                        avatar: Icon(p['icon'] as IconData, size: 16, color: isSelected ? Colors.black : color),
                        label: Text(p['title'] as String),
                        selectedColor: AppColors.yandexAmber,
                        backgroundColor: AppColors.surface,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.black : Colors.white,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 12,
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 14),

              // Description of selected preset
              Builder(builder: (context) {
                final cur = _presets.firstWhere((p) => p['id'] == _selectedPreset);
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.cardBorder),
                  ),
                  child: Row(
                    children: [
                      Icon(cur['icon'] as IconData, color: cur['color'] as Color, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          cur['desc'] as String,
                          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                        ),
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 18),

              // 2. Genre Dropdown (if genre preset)
              if (_selectedPreset == 'genre') ...[
                const Text(
                  'Жанровый кластер:',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.cardBorder),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _selectedGenre,
                      isExpanded: true,
                      dropdownColor: AppColors.surfaceElevated,
                      items: (widget.appViewModel.genres.isNotEmpty
                              ? widget.appViewModel.genres.map((g) => g.name).toList()
                              : [
                                  'Phonk & Memphis',
                                  'Heavy & Metal',
                                  'Dubstep & EDM',
                                  'Hip-Hop & Trap',
                                  'Rock & Alternative',
                                  'Other & Electronic',
                                ])
                          .map((genreName) {
                        return DropdownMenuItem<String>(
                          value: genreName,
                          child: Text(genreName, style: const TextStyle(fontSize: 14)),
                        );
                      }).toList(),
                      onChanged: (newGenre) {
                        if (newGenre != null) {
                          setState(() {
                            _selectedGenre = newGenre;
                            _updateDefaultTitle();
                          });
                        }
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 18),
              ],

              // 3. Playlist Title
              const Text(
                'Название плейлиста:',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _titleController,
                decoration: InputDecoration(
                  filled: true,
                  fillColor: AppColors.surface,
                  hintText: 'Введите название',
                  prefixIcon: const Icon(Icons.playlist_play_rounded, color: AppColors.yandexAmber),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: AppColors.cardBorder),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: AppColors.cardBorder),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: AppColors.yandexAmber),
                  ),
                ),
              ),
              const SizedBox(height: 18),

              // 4. Limit Selector
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Количество треков:',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textSecondary),
                      ),
                      Text(
                        _limit == 0 ? 'Все доступные треки' : '$_limit треков',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.yandexAmber),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      {'label': '50', 'val': 50},
                      {'label': '100', 'val': 100},
                      {'label': '200', 'val': 200},
                      {'label': '500', 'val': 500},
                      {'label': 'Все треки ♾️', 'val': 0},
                    ].map((item) {
                      final count = item['val'] as int;
                      final label = item['label'] as String;
                      final isSelected = _limit == count;
                      return ChoiceChip(
                        selected: isSelected,
                        onSelected: (val) {
                          if (val) setState(() => _limit = count);
                        },
                        label: Text(label),
                        selectedColor: AppColors.yandexAmber,
                        backgroundColor: AppColors.surface,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.black : Colors.white,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                          fontSize: 12,
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Error banner if any
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.yandexRed.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppColors.yandexRed.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline_rounded, color: AppColors.yandexRed, size: 20),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: const TextStyle(fontSize: 12, color: Colors.white),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Export Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: FilledButton.icon(
                  onPressed: widget.authViewModel.isExporting ? null : _export,
                  icon: widget.authViewModel.isExporting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                        )
                      : const Icon(Icons.cloud_upload_rounded),
                  label: Text(
                    widget.authViewModel.isExporting
                        ? 'Создание в Яндекс Музыке...'
                        : 'Создать плейлист в аккаунте',
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                  ),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.yandexAmber,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
