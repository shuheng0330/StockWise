import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/inventory_models.dart';
import '../state/providers.dart';
import '../widgets/shared_components.dart';
import '../widgets/simulation_modal.dart';

class DashboardScreen extends ConsumerWidget {
  final String analysisId;
  const DashboardScreen({super.key, required this.analysisId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analysis = ref.watch(analysisByIdProvider(analysisId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Records',
            onPressed: () => context.goNamed('records', pathParameters: {'analysisId': analysisId}),
            icon: const Icon(Icons.edit_note),
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: analysis == null
                ? const SoftSectionCard(
                    child: Text(
                      'This dashboard needs an in-memory analysis result.\n\nGo back and upload a CSV (the backend currently exposes only POST-based analysis creation).',
                      textAlign: TextAlign.center,
                    ),
                  )
                : _DashboardBody(analysis: analysis),
          ),
        ),
      ),
    );
  }
}

class _DashboardBody extends StatelessWidget {
  final AnalysisResponse analysis;
  const _DashboardBody({required this.analysis});

  String _money(double v) => '\$${v.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    final k = analysis.kpiSummary;
    final items = analysis.items;

    return ListView(
      children: [
        Wrap(
          runSpacing: 12,
          spacing: 12,
          children: [
            SizedBox(
              width: (MediaQuery.of(context).size.width - 16 * 2 - 12) / 2,
              child: KpiCard(title: 'Items', value: '${k.itemCount}', icon: Icons.inventory_2_outlined),
            ),
            SizedBox(
              width: (MediaQuery.of(context).size.width - 16 * 2 - 12) / 2,
              child: KpiCard(title: 'Value at risk', value: _money(k.inventoryValueAtRisk), icon: Icons.warning_amber_rounded),
            ),
            SizedBox(
              width: (MediaQuery.of(context).size.width - 16 * 2 - 12) / 2,
              child: KpiCard(title: 'Restock now', value: '${k.restockNowCount}', icon: Icons.local_shipping_outlined),
            ),
            SizedBox(
              width: (MediaQuery.of(context).size.width - 16 * 2 - 12) / 2,
              child: KpiCard(title: 'High waste risk', value: '${k.highWasteRiskCount}', icon: Icons.delete_outline),
            ),
          ],
        ),
        const SizedBox(height: 16),
        const Text('Ranked recommendations', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        ...items.map((item) => _ItemCard(item: item, analysisId: analysis.analysisId)),
        const SizedBox(height: 12),
      ],
    );
  }
}

class _ItemCard extends ConsumerWidget {
  final ItemAnalysis item;
  final String analysisId;
  const _ItemCard({required this.item, required this.analysisId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () async {
          await showModalBottomSheet<void>(
            context: context,
            isScrollControlled: true,
            showDragHandle: true,
            backgroundColor: Theme.of(context).cardColor,
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            ),
            builder: (context) => SimulationModal(
              analysisId: analysisId,
              item: item,
            ),
          );
        },
        child: SoftSectionCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      item.itemName,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 10),
                  RecommendationBadge(action: item.recommendedAction, compact: true),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  _MiniMetric(label: 'Stock', value: item.currentStock.toStringAsFixed(1)),
                  _MiniMetric(label: 'Cover (days)', value: item.daysOfCover.toStringAsFixed(1)),
                  ScoreBadge(label: 'Urgency', score: item.reorderUrgencyScore),
                  ScoreBadge(label: 'Waste', score: item.wasteRiskScore),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MiniMetric extends StatelessWidget {
  final String label;
  final String value;
  const _MiniMetric({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 11, color: Theme.of(context).hintColor, fontWeight: FontWeight.w600)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }
}

