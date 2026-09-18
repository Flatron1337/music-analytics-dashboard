import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';
import '../../state/app_view_model.dart';
import '../../state/yandex_auth_view_model.dart';
import '../widgets/server_settings_sheet.dart';
import 'overview_tab.dart';
import 'genres_tab.dart';
import 'timeline_tab.dart';
import 'tracks_tab.dart';
import 'profile_tab.dart';

class MainScreen extends StatefulWidget {
  final AppViewModel appViewModel;
  final YandexAuthViewModel authViewModel;

  const MainScreen({
    super.key,
    required this.appViewModel,
    required this.authViewModel,
  });

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  @override
  Widget build(BuildContext context) {
    final vm = widget.appViewModel;

    return ListenableBuilder(
      listenable: vm,
      builder: (context, _) {
        final tabs = [
          OverviewTab(viewModel: vm),
          GenresTab(viewModel: vm),
          TimelineTab(viewModel: vm),
          TracksTab(viewModel: vm),
          ProfileTab(appViewModel: vm, authViewModel: widget.authViewModel),
        ];

        return Scaffold(
          appBar: AppBar(
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppColors.yandexAmber.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.headphones_rounded, color: AppColors.yandexAmber, size: 20),
                ),
                const SizedBox(width: 10),
                const Text(
                  'Yandex Music',
                  style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: -0.3),
                ),
              ],
            ),
            actions: [
              // Server connection pill
              GestureDetector(
                onTap: () => ServerSettingsSheet.show(context, vm),
                child: Container(
                  margin: const EdgeInsets.only(right: 12),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceElevated,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: vm.isServerConnected
                          ? AppColors.neonGreen.withValues(alpha: 0.3)
                          : AppColors.yandexRed.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: vm.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        vm.isServerConnected ? 'API Online' : 'Offline',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: vm.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          body: IndexedStack(
            index: vm.selectedTabIndex,
            children: tabs,
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: vm.selectedTabIndex,
            onDestinationSelected: (idx) => vm.setTab(idx),
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard_rounded),
                label: 'Обзор',
              ),
              NavigationDestination(
                icon: Icon(Icons.pie_chart_outline_rounded),
                selectedIcon: Icon(Icons.pie_chart_rounded),
                label: 'Жанры',
              ),
              NavigationDestination(
                icon: Icon(Icons.timeline_rounded),
                selectedIcon: Icon(Icons.timeline_rounded),
                label: 'Таймлайн',
              ),
              NavigationDestination(
                icon: Icon(Icons.queue_music_outlined),
                selectedIcon: Icon(Icons.queue_music_rounded),
                label: 'Треки',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline_rounded),
                selectedIcon: Icon(Icons.person_rounded),
                label: 'Профиль',
              ),
            ],
          ),
        );
      },
    );
  }
}
