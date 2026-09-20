import 'package:flutter/material.dart';

class AppColors {
  // Backgrounds
  static const Color background = Color(0xFF0F0F12);
  static const Color surface = Color(0xFF18181F);
  static const Color surfaceElevated = Color(0xFF22222C);
  static const Color cardBorder = Color(0xFF2A2A38);

  // Accents
  static const Color yandexAmber = Color(0xFFFFCC00);
  static const Color yandexRed = Color(0xFFFF3333);
  static const Color neonPurple = Color(0xFF9D4EDD);
  static const Color neonCyan = Color(0xFF00E5FF);
  static const Color cyberCyan = Color(0xFF00E5FF);
  static const Color neonGreen = Color(0xFF00E676);

  // Text
  static const Color textPrimary = Color(0xFFF0F0F5);
  static const Color textSecondary = Color(0xFF9E9EA7);
  static const Color textMuted = Color(0xFF6B6B78);

  // Cluster Specific Colors
  static const Color dubstep = Color(0xFF00E5FF);
  static const Color metal = Color(0xFFFF3D00);
  static const Color phonk = Color(0xFFD500F9);
  static const Color hiphop = Color(0xFFFFD600);
  static const Color rock = Color(0xFF00E676);
  static const Color other = Color(0xFFB0BEC5);

  static Color getClusterColor(String clusterName) {
    if (clusterName.contains('Dubstep') || clusterName.contains('EDM')) {
      return dubstep;
    } else if (clusterName.contains('Metal')) {
      return metal;
    } else if (clusterName.contains('Phonk') || clusterName.contains('Memphis')) {
      return phonk;
    } else if (clusterName.contains('Hip-Hop') || clusterName.contains('Trap')) {
      return hiphop;
    } else if (clusterName.contains('Rock')) {
      return rock;
    }
    return other;
  }
}
