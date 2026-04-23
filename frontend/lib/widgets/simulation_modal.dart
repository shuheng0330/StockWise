import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/inventory_models.dart';
import '../services/api_service.dart';
import '../state/providers.dart';
import '../utils/error_handler.dart';
import 'explanation_drawer.dart';
import 'shared_components.dart';

class SimulationModal extends ConsumerStatefulWidget {
  final String analysisId;
  final ItemAnalysis item;

  const SimulationModal({
    super.key,
    required this.analysisId,
    required this.item,
  });

  @override
  ConsumerState<SimulationModal> createState() => _SimulationModalState();
}

class _SimulationModalState extends ConsumerState<SimulationModal> {
  final _qtyController = TextEditingController();
  Timer? _debounce;

  bool _loading = false;
  SimulationResponse? _simulation;
  Object? _lastError;

  @override
  void initState() {
    super.initState();
    _qtyController.text = '0';
    _triggerDebounced();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _qtyController.dispose();
    super.dispose();
  }

  void _triggerDebounced() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _simulate);
  }

  double _parseQty() {
    final t = _qtyController.text.trim();
    final v = double.tryParse(t);
    return (v == null || v.isNaN || v.isInfinite) ? 0 : v;
  }

  Future<void> _simulate() async {
    final qty = _parseQty();
    if (qty < 0) return;
    setState(() {
      _loading = true;
      _lastError = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final sim = await api.simulate(
        analysisId: widget.analysisId,
        itemId: widget.item.itemId,
        request: SimulationRequest(simulatedOrderQty: qty),
      );
      if (!mounted) return;
      setState(() => _simulation = sim);
      ref.read(analysisCacheProvider.notifier).applySimulation(widget.analysisId, sim);
    } catch (e) {
      if (!mounted) return;
      setState(() => _lastError = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _money(double v) => '\$${v.toStringAsFixed(2)}';

  @override
  Widget build(BuildContext context) {
    final sim = _simulation;
    final action = sim?.recommendedAction ?? widget.item.recommendedAction;

    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 8,
        bottom: 16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.item.itemName,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 10),
                RecommendationBadge(action: action, compact: true),
              ],
            ),
            const SizedBox(height: 12),
            SoftSectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Simulate reorder quantity', style: TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: FormInputField(
                          label: 'simulated_order_qty',
                          controller: _qtyController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          validator: null,
                        ),
                      ),
                      const SizedBox(width: 10),
                      SizedBox(
                        height: 46,
                        width: 120,
                        child: FilledButton(
                          onPressed: _loading ? null : _simulate,
                          child: _loading
                              ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Text('Run'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Slider(
                    value: _parseQty().clamp(0, 5000),
                    min: 0,
                    max: 5000,
                    divisions: 100,
                    label: _parseQty().toStringAsFixed(0),
                    onChanged: (v) {
                      _qtyController.text = v.toStringAsFixed(0);
                      _triggerDebounced();
                      setState(() {});
                    },
                  ),
                  if (_lastError != null) ...[
                    const SizedBox(height: 8),
                    TextButton.icon(
                      onPressed: () => showApiError(context, _lastError!),
                      icon: const Icon(Icons.error_outline),
                      label: const Text('Simulation failed. Tap for details.'),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 12),
            SoftSectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Simulation output', style: TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      _StatChip(label: 'Cash outlay', value: sim == null ? '—' : _money(sim.simulatedCashOutlay)),
                      _StatChip(label: 'Coverage (days)', value: sim == null ? '—' : sim.simulatedCoverageDays.toStringAsFixed(1)),
                      _StatChip(label: 'Inv. value', value: sim == null ? '—' : _money(sim.simulatedInventoryValue)),
                      _StatChip(
                        label: 'Waste cost',
                        value: sim == null ? '—' : _money(sim.simulatedEstimatedWasteCost),
                      ),
                      _StatChip(
                        label: 'Risk change',
                        value: sim == null ? '—' : simulatedRiskChangeToJson(sim.simulatedRiskChange),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: ScoreBadge(label: 'Urgency', score: sim?.reorderUrgencyScore ?? widget.item.reorderUrgencyScore)),
                      const SizedBox(width: 10),
                      Expanded(child: ScoreBadge(label: 'Waste', score: sim?.wasteRiskScore ?? widget.item.wasteRiskScore)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            ExplanationDrawer(
              analysisId: widget.analysisId,
              itemId: widget.item.itemId,
              itemName: widget.item.itemName,
              currentRecommendedAction: action,
              simulation: sim,
            ),
          ],
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label;
  final String value;
  const _StatChip({required this.label, required this.value});

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

