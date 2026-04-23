import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/inventory_models.dart';
import '../services/api_service.dart';

final apiBaseUrlProvider = Provider<String>((ref) {
  return const String.fromEnvironment('STOCKWISE_API_BASE_URL', defaultValue: 'http://localhost:8000');
});

final apiServiceProvider = Provider<ApiService>((ref) {
  final baseUrl = ref.watch(apiBaseUrlProvider);
  return ApiService(baseUrl: baseUrl);
});

class AnalysisCache extends StateNotifier<Map<String, AnalysisResponse>> {
  AnalysisCache() : super(const {});

  void upsert(AnalysisResponse analysis) {
    state = {...state, analysis.analysisId: analysis};
  }

  void applySimulation(String analysisId, SimulationResponse sim) {
    final current = state[analysisId];
    if (current == null) return;
    final updatedItems = current.items
        .map((it) => it.itemId == sim.itemId
            ? ItemAnalysis(
                itemId: it.itemId,
                date: it.date,
                itemName: it.itemName,
                category: it.category,
                subcategory: it.subcategory,
                unit: it.unit,
                supplierName: it.supplierName,
                currentStock: it.currentStock,
                reorderLevel: it.reorderLevel,
                dailyUsage: it.dailyUsage,
                leadTime: it.leadTime,
                pricePerUnit: it.pricePerUnit,
                seasonalFactor: it.seasonalFactor,
                wastePercentage: it.wastePercentage,
                avgUsage7d: it.avgUsage7d,
                trendDirection: it.trendDirection,
                daysOfCover: it.daysOfCover,
                inventoryValue: sim.simulatedInventoryValue,
                estimatedWasteCost: sim.simulatedEstimatedWasteCost,
                leadTimeDemand: it.leadTimeDemand,
                stockGapToLeadDemand: it.stockGapToLeadDemand,
                reorderUrgencyScore: sim.reorderUrgencyScore,
                wasteRiskScore: sim.wasteRiskScore,
                recommendedAction: sim.recommendedAction,
              )
            : it)
        .toList();

    state = {
      ...state,
      analysisId: AnalysisResponse(
        analysisId: current.analysisId,
        datasetSummary: current.datasetSummary,
        kpiSummary: current.kpiSummary,
        items: updatedItems,
      ),
    };
  }
}

final analysisCacheProvider = StateNotifierProvider<AnalysisCache, Map<String, AnalysisResponse>>((ref) {
  return AnalysisCache();
});

final analysisByIdProvider = Provider.family<AnalysisResponse?, String>((ref, analysisId) {
  final cache = ref.watch(analysisCacheProvider);
  return cache[analysisId];
});

