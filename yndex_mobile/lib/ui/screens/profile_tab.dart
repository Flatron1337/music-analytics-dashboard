import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/theme/app_colors.dart';
import '../../state/app_view_model.dart';
import '../../state/yandex_auth_view_model.dart';
import '../widgets/server_settings_sheet.dart';

class ProfileTab extends StatelessWidget {
  final AppViewModel appViewModel;
  final YandexAuthViewModel authViewModel;

  const ProfileTab({
    super.key,
    required this.appViewModel,
    required this.authViewModel,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: authViewModel,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Профиль и интеграции',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            Text(
              'Управление подключением к Яндекс Музыке и бэкенду',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 20),

            // Yandex Music Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: authViewModel.isAuthenticated
                      ? AppColors.neonGreen.withValues(alpha: 0.5)
                      : AppColors.yandexAmber.withValues(alpha: 0.5),
                  width: 1.5,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.yandexRed.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.music_note_rounded, color: AppColors.yandexRed, size: 28),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Яндекс Музыка',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            Row(
                              children: [
                                Icon(
                                  authViewModel.isAuthenticated ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
                                  size: 14,
                                  color: authViewModel.isAuthenticated ? AppColors.neonGreen : AppColors.textMuted,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  authViewModel.isAuthenticated ? 'Аккаунт подключен' : 'Не авторизован',
                                  style: TextStyle(
                                    color: authViewModel.isAuthenticated ? AppColors.neonGreen : AppColors.textMuted,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  if (authViewModel.isAuthenticated) ...[
                    Text(
                      'Вы можете синхронизировать свежие лайки напрямую из своего аккаунта.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: authViewModel.isSyncing
                                ? null
                                : () async {
                                    final ok = await authViewModel.syncLikes();
                                    if (ok) {
                                      appViewModel.loadDashboardData(forceRefresh: true);
                                    }
                                  },
                            icon: authViewModel.isSyncing
                                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                                : const Icon(Icons.sync_rounded),
                            label: Text(authViewModel.isSyncing ? 'Синхронизация...' : 'Синхронизировать лайки'),
                            style: FilledButton.styleFrom(
                              backgroundColor: AppColors.yandexAmber,
                              foregroundColor: Colors.black,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton.outlined(
                          icon: const Icon(Icons.logout_rounded, color: AppColors.yandexRed),
                          tooltip: 'Выйти',
                          onPressed: () => authViewModel.logout(),
                        ),
                      ],
                    ),
                  ] else ...[
                    Text(
                      'Для синхронизации и создания плейлистов войдите через официальный Device Flow (ya.ru/device):',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 14),

                    if (authViewModel.userCode != null) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceElevated,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.cardBorder),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Твой код для входа:', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                                const SizedBox(height: 2),
                                Text(
                                  authViewModel.userCode!,
                                  style: const TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 2,
                                    color: AppColors.yandexAmber,
                                  ),
                                ),
                              ],
                            ),
                            IconButton(
                              icon: const Icon(Icons.copy_rounded, color: AppColors.textSecondary),
                              tooltip: 'Скопировать код',
                              onPressed: () {
                                Clipboard.setData(ClipboardData(text: authViewModel.userCode!));
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Код скопирован в буфер обмена')),
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton.icon(
                              onPressed: () => authViewModel.openVerificationUrl(),
                              icon: const Icon(Icons.open_in_browser_rounded),
                              label: const Text('Открыть ya.ru/device'),
                              style: FilledButton.styleFrom(
                                backgroundColor: AppColors.yandexAmber,
                                foregroundColor: Colors.black,
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (authViewModel.isPolling) ...[
                        const SizedBox(height: 10),
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                            SizedBox(width: 8),
                            Text('Ожидание подтверждения на ya.ru/device...', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                          ],
                        ),
                      ],
                    ] else ...[
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: authViewModel.isRequestingCode
                              ? null
                              : () => authViewModel.startDeviceFlow(),
                          icon: authViewModel.isRequestingCode
                              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.login_rounded),
                          label: const Text('Войти через Яндекс'),
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.yandexAmber,
                            foregroundColor: Colors.black,
                          ),
                        ),
                      ),
                    ],
                  ],

                  if (authViewModel.statusMessage != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      authViewModel.statusMessage!,
                      style: TextStyle(
                        color: authViewModel.isAuthenticated ? AppColors.neonGreen : AppColors.yandexAmber,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Server Connection Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.cardBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.dns_rounded,
                            color: appViewModel.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'Сервер аналитики',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ],
                      ),
                      TextButton(
                        onPressed: () => ServerSettingsSheet.show(context, appViewModel),
                        child: const Text('Изменить'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    appViewModel.serverUrl.isNotEmpty ? appViewModel.serverUrl : 'Не задан',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: appViewModel.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        appViewModel.isServerConnected ? 'Подключено (Порт 5001)' : 'Сервер не отвечает',
                        style: TextStyle(
                          fontSize: 12,
                          color: appViewModel.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // App About
            Center(
              child: Column(
                children: [
                  const Text('Music Analytics Mobile v1.0.0', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                  const SizedBox(height: 2),
                  const Text('Flutter + Python REST API', style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
