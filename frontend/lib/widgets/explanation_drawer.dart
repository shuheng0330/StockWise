import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/inventory_models.dart';
import '../state/providers.dart';
import '../theme/app_theme.dart';
import '../utils/error_handler.dart';
import 'shared_components.dart';

class ExplanationDrawer extends ConsumerStatefulWidget {
  final String analysisId;
  final int itemId;
  final String itemName;
  final RecommendedAction currentRecommendedAction;
  final SimulationResponse? simulation;

  const ExplanationDrawer({
    super.key,
    required this.analysisId,
    required this.itemId,
    required this.itemName,
    required this.currentRecommendedAction,
    required this.simulation,
  });

  @override
  ConsumerState<ExplanationDrawer> createState() => _ExplanationDrawerState();
}

class _ExplanationDrawerState extends ConsumerState<ExplanationDrawer> with SingleTickerProviderStateMixin {
  bool _loading = false;
  ExplanationResponse? _explanation;
  Object? _error;

  late final AnimationController _shimmer = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat();

  @override
  void dispose() {
    _shimmer.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final sim = widget.simulation;
      final req = ExplanationRequest(
        simulatedOrderQty: sim?.simulatedOrderQty,
        simulatedCashOutlay: sim?.simulatedCashOutlay,
        simulatedCoverageDays: sim?.simulatedCoverageDays,
        simulatedRiskChange: sim == null ? null : simulatedRiskChangeToJson(sim.simulatedRiskChange),
      );
      final exp = await api.explanation(
        analysisId: widget.analysisId,
        itemId: widget.itemId,
        request: req,
      );
      if (!mounted) return;
      setState(() => _explanation = exp);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final exp = _explanation;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: [
            StockWiseColors.purple.withValues(alpha: 0.20),
            StockWiseColors.indigo.withValues(alpha: 0.10),
          ],
        ),
        border: Border.all(color: StockWiseColors.purple.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome, size: 18, color: StockWiseColors.purple),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('AI Explanation', style: TextStyle(fontWeight: FontWeight.w900)),
              ),
              RecommendationBadge(action: widget.currentRecommendedAction, compact: true),
            ],
          ),
          const SizedBox(height: 10),
          if (exp == null && !_loading) ...[
            PrimaryButton(label: 'Generate explanation', icon: Icons.psychology, onPressed: _load),
          ] else if (_loading) ...[
            _ShimmerBlock(controller: _shimmer, lines: 5),
          ] else ...[
            Text(
              'Source: ${explanationSourceToJson(exp!.source)} • Priority: ${priorityLevelToJson(exp.priorityLevel)}',
              style: TextStyle(color: Theme.of(context).hintColor, fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 10),
            _Section(title: 'Short reason', body: exp.shortReason),
            const SizedBox(height: 10),
            _Section(title: 'Decision explanation', body: exp.decisionExplanation),
            const SizedBox(height: 10),
            _Section(title: 'Tradeoffs', body: exp.tradeoffSummary),
            const SizedBox(height: 10),
            _Section(title: 'Suggested next step', body: exp.suggestedNextStep),
            const SizedBox(height: 10),
            _Section(title: 'Confidence note', body: exp.confidenceNote),
            const SizedBox(height: 10),
            _Section(title: 'Warning flag', body: exp.warningFlag),
            const SizedBox(height: 12),
            SecondaryButton(label: 'Regenerate', icon: Icons.refresh, onPressed: _load),
          ],
          if (_error != null) ...[
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () => showApiError(context, _error!),
              icon: const Icon(Icons.error_outline),
              label: const Text('Explanation failed. Tap for details.'),
            ),
          ],
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final String body;
  const _Section({required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    return SoftSectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 6),
          Text(body),
        ],
      ),
    );
  }
}

class _ShimmerBlock extends StatelessWidget {
  final AnimationController controller;
  final int lines;

  const _ShimmerBlock({required this.controller, required this.lines});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final t = controller.value;
        final start = (t * 2 - 1).clamp(-1.0, 1.0);
        return Column(
          children: List.generate(lines, (i) {
            final h = i == 0 ? 14.0 : 12.0;
            final w = i == lines - 1 ? 0.72 : 1.0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: FractionallySizedBox(
                widthFactor: w,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: ShaderMask(
                    shaderCallback: (rect) {
                      return LinearGradient(
                        begin: Alignment(-1 + start, 0),
                        end: Alignment(1 + start, 0),
                        colors: [
                          Colors.white.withValues(alpha: 0.35),
                          Colors.white.withValues(alpha: 0.60),
                          Colors.white.withValues(alpha: 0.35),
                        ],
                      ).createShader(rect);
                    },
                    blendMode: BlendMode.srcATop,
                    child: Container(
                      height: h,
                      color: StockWiseColors.slate100.withValues(alpha: 0.35),
                    ),
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

