import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';
import 'data/repositories/music_repository.dart';
import 'data/services/api_service.dart';
import 'state/app_view_model.dart';
import 'state/yandex_auth_view_model.dart';
import 'ui/screens/main_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final apiService = ApiService();
  final musicRepository = MusicRepository(apiService: apiService);

  final appViewModel = AppViewModel(repository: musicRepository);
  final authViewModel = YandexAuthViewModel(apiService: apiService);

  // Initialize and load initial data
  await appViewModel.init();

  runApp(
    MusicAnalyticsApp(
      appViewModel: appViewModel,
      authViewModel: authViewModel,
    ),
  );
}

class MusicAnalyticsApp extends StatelessWidget {
  final AppViewModel appViewModel;
  final YandexAuthViewModel authViewModel;

  const MusicAnalyticsApp({
    super.key,
    required this.appViewModel,
    required this.authViewModel,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Yandex Music Analytics',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: MainScreen(
        appViewModel: appViewModel,
        authViewModel: authViewModel,
      ),
    );
  }
}
