import 'package:flutter/material.dart';

class GenreCluster {
  final String name;
  final int count;
  final double percent;
  final String colorHex;
  final String iconName;

  GenreCluster({
    required this.name,
    required this.count,
    required this.percent,
    required this.colorHex,
    required this.iconName,
  });

  Color get color {
    try {
      final clean = colorHex.replaceFirst('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.amber;
    }
  }

  IconData get icon {
    switch (iconName) {
      case 'electric_bolt':
        return Icons.electric_bolt_rounded;
      case 'local_fire_department':
        return Icons.local_fire_department_rounded;
      case 'speed':
        return Icons.speed_rounded;
      case 'mic':
        return Icons.mic_external_on_rounded;
      case 'graphic_eq':
        return Icons.graphic_eq_rounded;
      case 'category':
        return Icons.auto_awesome_rounded;
      default:
        return Icons.music_note_rounded;
    }
  }

  factory GenreCluster.fromJson(Map<String, dynamic> json) {
    return GenreCluster(
      name: json['name'] as String? ?? 'Other',
      count: (json['count'] as num?)?.toInt() ?? 0,
      percent: (json['percent'] as num?)?.toDouble() ?? 0.0,
      colorHex: json['color'] as String? ?? '#FFCC00',
      iconName: json['icon'] as String? ?? 'music_note',
    );
  }
}
