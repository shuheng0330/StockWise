import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import 'routing/app_router.dart';
import 'theme/app_theme.dart';

class StockWiseApp extends ConsumerWidget {
  const StockWiseApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(appRouterProvider);
    final light = buildStockWiseTheme(Brightness.light);
    final dark = buildStockWiseTheme(Brightness.dark);

    return MaterialApp.router(
      title: 'StockWise',
      theme: light.copyWith(textTheme: GoogleFonts.interTextTheme(light.textTheme)),
      darkTheme: dark.copyWith(textTheme: GoogleFonts.interTextTheme(dark.textTheme)),
      themeMode: ThemeMode.light,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

