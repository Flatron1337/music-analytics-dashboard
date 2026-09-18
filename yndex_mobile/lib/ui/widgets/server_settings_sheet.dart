import 'package:flutter/material.dart';
import '../../core/constants/api_constants.dart';
import '../../core/theme/app_colors.dart';
import '../../state/app_view_model.dart';

class ServerSettingsSheet extends StatefulWidget {
  final AppViewModel viewModel;

  const ServerSettingsSheet({super.key, required this.viewModel});

  static Future<void> show(BuildContext context, AppViewModel viewModel) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => ServerSettingsSheet(viewModel: viewModel),
    );
  }

  @override
  State<ServerSettingsSheet> createState() => _ServerSettingsSheetState();
}

class _ServerSettingsSheetState extends State<ServerSettingsSheet> {
  late final TextEditingController _controller;
  bool _isTesting = false;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.viewModel.serverUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _applyUrl(String url) async {
    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    _controller.text = url;
    await widget.viewModel.updateServerUrl(url);

    setState(() {
      _isTesting = false;
      _testResult = widget.viewModel.isServerConnected
          ? '✅ Успешно подключено к серверу!'
          : '❌ Сервер недоступен по этому адресу';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Настройки бэкенда',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Укажите адрес Python REST API для получения аналитики.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _controller,
            decoration: InputDecoration(
              labelText: 'URL сервера',
              hintText: 'http://192.168.1.50:5001',
              suffixIcon: IconButton(
                icon: const Icon(Icons.check_circle_rounded, color: AppColors.yandexAmber),
                onPressed: () => _applyUrl(_controller.text),
              ),
            ),
          ),
          const SizedBox(height: 12),
          if (_isTesting)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Row(
                children: [
                  SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                  SizedBox(width: 12),
                  Text('Проверка подключения...'),
                ],
              ),
            )
          else if (_testResult != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text(
                _testResult!,
                style: TextStyle(
                  color: widget.viewModel.isServerConnected ? AppColors.neonGreen : AppColors.yandexRed,
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ),
          const SizedBox(height: 16),
          Text(
            'Быстрый выбор адреса:',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ActionChip(
                label: const Text('Localhost (ПК)'),
                onPressed: () => _applyUrl(ApiConstants.defaultLocalHost),
              ),
              ActionChip(
                label: const Text('Android Эмулятор'),
                onPressed: () => _applyUrl(ApiConstants.defaultAndroidEmulator),
              ),
              ActionChip(
                label: const Text('Render Cloud'),
                onPressed: () => _applyUrl(ApiConstants.defaultRenderHost),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
