import 'package:flutter/material.dart';
import 'config/app_config.dart';
import 'config/app_theme.dart';
import 'screens/splash_screen.dart';

void main() {
  runApp(const TaniAdaptifApp());
}

class TaniAdaptifApp extends StatelessWidget {
  const TaniAdaptifApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.namaAplikasi,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const SplashScreen(),
    );
  }
}
