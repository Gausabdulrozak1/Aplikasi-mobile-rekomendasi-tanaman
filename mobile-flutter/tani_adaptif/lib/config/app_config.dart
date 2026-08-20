import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

class AppConfig {
  static const String environment = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'development',
  );
  static const bool mockMode = bool.fromEnvironment(
    'MOCK_MODE',
    defaultValue: false,
  );
  static const String _backendOverride = String.fromEnvironment(
    'BACKEND_API_BASE_URL',
  );
  static const String backendVisualApiToken = String.fromEnvironment(
    'BACKEND_VISUAL_API_TOKEN',
  );

  static String get baseUrl => _backendOverride.isNotEmpty
      ? _backendOverride
      : kIsWeb
      ? 'http://localhost:3000/api'
      : 'http://10.0.2.2:3000/api';

  static const String kodeWilayahAikmel = '52.03.09.2002';
  static const String namaAplikasi = 'TaniAdaptif';

  static Map<String, String> get visualImageHeaders =>
      backendVisualApiToken.isEmpty
      ? const <String, String>{}
      : const <String, String>{'X-Client-Token': backendVisualApiToken};

  static bool get isProduction => environment == 'production';
}

class AppColors {
  static const Color primary = Color(0xFF2D6A4F);
  static const Color primaryLight = Color(0xFF40916C);
  static const Color primaryLightest = Color(0xFFD8F3DC);

  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF1F1F1F);
  static const Color grey = Color(0xFF757575);
  static const Color greyLight = Color(0xFFF0F0F0);
  static const Color background = Color(0xFFF8F9FA);

  static const Color success = Color(0xFF4CAF50);
  static const Color warning = Color(0xFFFFA726);
  static const Color danger = Color(0xFFEF5350);
  static const Color info = Color(0xFF42A5F5);
}
