import 'package:flutter/material.dart';

class StockWiseColors {
  static const slate900 = Color(0xFF0F172A);
  static const slate800 = Color(0xFF1E293B);
  static const slate700 = Color(0xFF334155);
  static const slate600 = Color(0xFF475569);
  static const slate200 = Color(0xFFE2E8F0);
  static const slate100 = Color(0xFFF1F5F9);
  static const offWhite = Color(0xFFF8FAFC);

  static const rose = Color(0xFFF43F5E);
  static const amber = Color(0xFFF59E0B);
  static const emerald = Color(0xFF10B981);
  static const indigo = Color(0xFF6366F1);
  static const purple = Color(0xFF8B5CF6);
}

ThemeData buildStockWiseTheme(Brightness brightness) {
  final isDark = brightness == Brightness.dark;
  final radius = BorderRadius.circular(16);

  final base = ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: StockWiseColors.slate900,
      brightness: brightness,
      surface: isDark ? StockWiseColors.slate900 : StockWiseColors.offWhite,
      background: isDark ? StockWiseColors.slate900 : StockWiseColors.offWhite,
    ),
  );

  return base.copyWith(
    scaffoldBackgroundColor: isDark ? StockWiseColors.slate900 : StockWiseColors.offWhite,
    appBarTheme: AppBarTheme(
      elevation: 0,
      backgroundColor: isDark ? StockWiseColors.slate900 : StockWiseColors.offWhite,
      foregroundColor: isDark ? StockWiseColors.offWhite : StockWiseColors.slate900,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: isDark ? StockWiseColors.slate800 : Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: radius),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: isDark ? StockWiseColors.slate800 : Colors.white,
      border: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: StockWiseColors.slate200)),
      enabledBorder: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: StockWiseColors.slate200)),
      focusedBorder: OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: StockWiseColors.slate700, width: 1.2)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: isDark ? StockWiseColors.slate800 : StockWiseColors.slate900,
      contentTextStyle: const TextStyle(color: StockWiseColors.offWhite),
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: radius),
    ),
    dividerTheme: DividerThemeData(color: isDark ? StockWiseColors.slate700 : StockWiseColors.slate200),
  );
}

