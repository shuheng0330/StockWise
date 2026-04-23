import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../screens/dashboard_screen.dart';
import '../screens/entry_screen.dart';
import '../screens/records_edit_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    routes: [
      GoRoute(
        path: '/',
        name: 'entry',
        builder: (context, state) => const EntryScreen(),
      ),
      GoRoute(
        path: '/analysis/:analysisId',
        name: 'dashboard',
        builder: (context, state) {
          final analysisId = state.pathParameters['analysisId']!;
          return DashboardScreen(analysisId: analysisId);
        },
        routes: [
          GoRoute(
            path: 'records',
            name: 'records',
            builder: (context, state) {
              final analysisId = state.pathParameters['analysisId']!;
              return RecordsEditScreen(analysisId: analysisId);
            },
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('StockWise')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            state.error?.toString() ?? 'Navigation error.',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    ),
  );
});

