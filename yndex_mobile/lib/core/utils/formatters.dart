import 'package:intl/intl.dart';

class Formatters {
  static final NumberFormat _numFormat = NumberFormat('#,###', 'ru_RU');

  static String formatNumber(num number) {
    return _numFormat.format(number).replaceAll(',', ' ');
  }

  static String formatSecondsToMinutes(int totalSeconds) {
    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  static String formatDurationDetailed(int totalSeconds) {
    final hours = totalSeconds ~/ 3600;
    final minutes = (totalSeconds % 3600) ~/ 60;
    final days = hours ~/ 24;
    final remHours = hours % 24;

    final parts = <String>[];
    if (days > 0) parts.add('$days дн.');
    if (remHours > 0 || days > 0) parts.add('$remHours ч.');
    parts.add('$minutes мин.');
    return parts.join(' ');
  }
}
