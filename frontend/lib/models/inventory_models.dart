// Models mapped from backend Pydantic schemas in `src/stockwise_api/schemas.py`
// plus request shapes specified in `frontend-pages-and-fields.md`.

import 'dart:convert';

String _requireString(Map<String, dynamic> json, String key) {
  final v = json[key];
  if (v is String) return v;
  throw FormatException('Expected "$key" to be a string.');
}

int _requireInt(Map<String, dynamic> json, String key) {
  final v = json[key];
  if (v is int) return v;
  if (v is num) return v.toInt();
  throw FormatException('Expected "$key" to be an int.');
}

double _requireDouble(Map<String, dynamic> json, String key) {
  final v = json[key];
  if (v is double) return v;
  if (v is int) return v.toDouble();
  if (v is num) return v.toDouble();
  throw FormatException('Expected "$key" to be a number.');
}

T? _nullable<T>(Map<String, dynamic> json, String key) => json[key] as T?;

enum TrendDirection { up, down, stable }

TrendDirection trendDirectionFromJson(String v) => switch (v) {
      'up' => TrendDirection.up,
      'down' => TrendDirection.down,
      'stable' => TrendDirection.stable,
      _ => throw FormatException('Unknown trend_direction: $v'),
    };

String trendDirectionToJson(TrendDirection v) => switch (v) {
      TrendDirection.up => 'up',
      TrendDirection.down => 'down',
      TrendDirection.stable => 'stable',
    };

enum RecommendedAction { restockNow, buyLess, delayPurchase, monitorClosely }

RecommendedAction recommendedActionFromJson(String v) => switch (v) {
      'RESTOCK_NOW' => RecommendedAction.restockNow,
      'BUY_LESS' => RecommendedAction.buyLess,
      'DELAY_PURCHASE' => RecommendedAction.delayPurchase,
      'MONITOR_CLOSELY' => RecommendedAction.monitorClosely,
      _ => throw FormatException('Unknown recommended_action: $v'),
    };

String recommendedActionToJson(RecommendedAction v) => switch (v) {
      RecommendedAction.restockNow => 'RESTOCK_NOW',
      RecommendedAction.buyLess => 'BUY_LESS',
      RecommendedAction.delayPurchase => 'DELAY_PURCHASE',
      RecommendedAction.monitorClosely => 'MONITOR_CLOSELY',
    };

class ErrorEnvelope {
  final String errorCode;
  final String message;
  final dynamic details;

  const ErrorEnvelope({required this.errorCode, required this.message, this.details});

  factory ErrorEnvelope.fromJson(Map<String, dynamic> json) => ErrorEnvelope(
        errorCode: _requireString(json, 'error_code'),
        message: _requireString(json, 'message'),
        details: json['details'],
      );

  Map<String, dynamic> toJson() => {'error_code': errorCode, 'message': message, 'details': details};

  @override
  String toString() => jsonEncode(toJson());
}

class DateRange {
  final String start;
  final String end;

  const DateRange({required this.start, required this.end});

  factory DateRange.fromJson(Map<String, dynamic> json) => DateRange(
        start: _requireString(json, 'start'),
        end: _requireString(json, 'end'),
      );

  Map<String, dynamic> toJson() => {'start': start, 'end': end};
}

class DatasetSummary {
  final int rowCount;
  final int itemCount;
  final DateRange dateRange;

  const DatasetSummary({required this.rowCount, required this.itemCount, required this.dateRange});

  factory DatasetSummary.fromJson(Map<String, dynamic> json) => DatasetSummary(
        rowCount: _requireInt(json, 'row_count'),
        itemCount: _requireInt(json, 'item_count'),
        dateRange: DateRange.fromJson((json['date_range'] as Map).cast<String, dynamic>()),
      );

  Map<String, dynamic> toJson() => {
        'row_count': rowCount,
        'item_count': itemCount,
        'date_range': dateRange.toJson(),
      };
}

class KpiSummary {
  final int itemCount;
  final int restockNowCount;
  final int buyLessCount;
  final int highWasteRiskCount;
  final double inventoryValueAtRisk;
  final List<String> topUrgentItems;
  final List<String> topWasteCostItems;

  const KpiSummary({
    required this.itemCount,
    required this.restockNowCount,
    required this.buyLessCount,
    required this.highWasteRiskCount,
    required this.inventoryValueAtRisk,
    required this.topUrgentItems,
    required this.topWasteCostItems,
  });

  factory KpiSummary.fromJson(Map<String, dynamic> json) => KpiSummary(
        itemCount: _requireInt(json, 'item_count'),
        restockNowCount: _requireInt(json, 'restock_now_count'),
        buyLessCount: _requireInt(json, 'buy_less_count'),
        highWasteRiskCount: _requireInt(json, 'high_waste_risk_count'),
        inventoryValueAtRisk: _requireDouble(json, 'inventory_value_at_risk'),
        topUrgentItems: (json['top_urgent_items'] as List).map((e) => e.toString()).toList(),
        topWasteCostItems: (json['top_waste_cost_items'] as List).map((e) => e.toString()).toList(),
      );

  Map<String, dynamic> toJson() => {
        'item_count': itemCount,
        'restock_now_count': restockNowCount,
        'buy_less_count': buyLessCount,
        'high_waste_risk_count': highWasteRiskCount,
        'inventory_value_at_risk': inventoryValueAtRisk,
        'top_urgent_items': topUrgentItems,
        'top_waste_cost_items': topWasteCostItems,
      };
}

class ItemAnalysis {
  final int itemId;
  final String date;
  final String itemName;
  final String category;
  final String subcategory;
  final String unit;
  final String supplierName;
  final double currentStock;
  final double reorderLevel;
  final double dailyUsage;
  final int leadTime;
  final double pricePerUnit;
  final double seasonalFactor;
  final double wastePercentage;
  final double avgUsage7d;
  final TrendDirection trendDirection;
  final double daysOfCover;
  final double inventoryValue;
  final double estimatedWasteCost;
  final double leadTimeDemand;
  final double stockGapToLeadDemand;
  final int reorderUrgencyScore;
  final int wasteRiskScore;
  final RecommendedAction recommendedAction;

  const ItemAnalysis({
    required this.itemId,
    required this.date,
    required this.itemName,
    required this.category,
    required this.subcategory,
    required this.unit,
    required this.supplierName,
    required this.currentStock,
    required this.reorderLevel,
    required this.dailyUsage,
    required this.leadTime,
    required this.pricePerUnit,
    required this.seasonalFactor,
    required this.wastePercentage,
    required this.avgUsage7d,
    required this.trendDirection,
    required this.daysOfCover,
    required this.inventoryValue,
    required this.estimatedWasteCost,
    required this.leadTimeDemand,
    required this.stockGapToLeadDemand,
    required this.reorderUrgencyScore,
    required this.wasteRiskScore,
    required this.recommendedAction,
  });

  factory ItemAnalysis.fromJson(Map<String, dynamic> json) => ItemAnalysis(
        itemId: _requireInt(json, 'item_id'),
        date: _requireString(json, 'date'),
        itemName: _requireString(json, 'item_name'),
        category: _requireString(json, 'category'),
        subcategory: _requireString(json, 'subcategory'),
        unit: _requireString(json, 'unit'),
        supplierName: _requireString(json, 'supplier_name'),
        currentStock: _requireDouble(json, 'current_stock'),
        reorderLevel: _requireDouble(json, 'reorder_level'),
        dailyUsage: _requireDouble(json, 'daily_usage'),
        leadTime: _requireInt(json, 'lead_time'),
        pricePerUnit: _requireDouble(json, 'price_per_unit'),
        seasonalFactor: _requireDouble(json, 'seasonal_factor'),
        wastePercentage: _requireDouble(json, 'waste_percentage'),
        avgUsage7d: _requireDouble(json, 'avg_usage_7d'),
        trendDirection: trendDirectionFromJson(_requireString(json, 'trend_direction')),
        daysOfCover: _requireDouble(json, 'days_of_cover'),
        inventoryValue: _requireDouble(json, 'inventory_value'),
        estimatedWasteCost: _requireDouble(json, 'estimated_waste_cost'),
        leadTimeDemand: _requireDouble(json, 'lead_time_demand'),
        stockGapToLeadDemand: _requireDouble(json, 'stock_gap_to_lead_demand'),
        reorderUrgencyScore: _requireInt(json, 'reorder_urgency_score'),
        wasteRiskScore: _requireInt(json, 'waste_risk_score'),
        recommendedAction: recommendedActionFromJson(_requireString(json, 'recommended_action')),
      );

  Map<String, dynamic> toJson() => {
        'item_id': itemId,
        'date': date,
        'item_name': itemName,
        'category': category,
        'subcategory': subcategory,
        'unit': unit,
        'supplier_name': supplierName,
        'current_stock': currentStock,
        'reorder_level': reorderLevel,
        'daily_usage': dailyUsage,
        'lead_time': leadTime,
        'price_per_unit': pricePerUnit,
        'seasonal_factor': seasonalFactor,
        'waste_percentage': wastePercentage,
        'avg_usage_7d': avgUsage7d,
        'trend_direction': trendDirectionToJson(trendDirection),
        'days_of_cover': daysOfCover,
        'inventory_value': inventoryValue,
        'estimated_waste_cost': estimatedWasteCost,
        'lead_time_demand': leadTimeDemand,
        'stock_gap_to_lead_demand': stockGapToLeadDemand,
        'reorder_urgency_score': reorderUrgencyScore,
        'waste_risk_score': wasteRiskScore,
        'recommended_action': recommendedActionToJson(recommendedAction),
      };
}

class AnalysisResponse {
  final String analysisId;
  final DatasetSummary datasetSummary;
  final KpiSummary kpiSummary;
  final List<ItemAnalysis> items;

  const AnalysisResponse({
    required this.analysisId,
    required this.datasetSummary,
    required this.kpiSummary,
    required this.items,
  });

  factory AnalysisResponse.fromJson(Map<String, dynamic> json) => AnalysisResponse(
        analysisId: _requireString(json, 'analysis_id'),
        datasetSummary: DatasetSummary.fromJson((json['dataset_summary'] as Map).cast<String, dynamic>()),
        kpiSummary: KpiSummary.fromJson((json['kpi_summary'] as Map).cast<String, dynamic>()),
        items: (json['items'] as List)
            .map((e) => ItemAnalysis.fromJson((e as Map).cast<String, dynamic>()))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'analysis_id': analysisId,
        'dataset_summary': datasetSummary.toJson(),
        'kpi_summary': kpiSummary.toJson(),
        'items': items.map((e) => e.toJson()).toList(),
      };
}

class SimulationRequest {
  final double simulatedOrderQty;
  const SimulationRequest({required this.simulatedOrderQty});
  Map<String, dynamic> toJson() => {'simulated_order_qty': simulatedOrderQty};
}

enum SimulatedRiskChange { lowerShortageRisk, lowerWasteRisk, higherWasteRisk, minimalChange }

SimulatedRiskChange simulatedRiskChangeFromJson(String v) => switch (v) {
      'lower_shortage_risk' => SimulatedRiskChange.lowerShortageRisk,
      'lower_waste_risk' => SimulatedRiskChange.lowerWasteRisk,
      'higher_waste_risk' => SimulatedRiskChange.higherWasteRisk,
      'minimal_change' => SimulatedRiskChange.minimalChange,
      _ => throw FormatException('Unknown simulated_risk_change: $v'),
    };

String simulatedRiskChangeToJson(SimulatedRiskChange v) => switch (v) {
      SimulatedRiskChange.lowerShortageRisk => 'lower_shortage_risk',
      SimulatedRiskChange.lowerWasteRisk => 'lower_waste_risk',
      SimulatedRiskChange.higherWasteRisk => 'higher_waste_risk',
      SimulatedRiskChange.minimalChange => 'minimal_change',
    };

class SimulationResponse {
  final int itemId;
  final double simulatedOrderQty;
  final double simulatedCashOutlay;
  final double simulatedCoverageDays;
  final double simulatedInventoryValue;
  final double simulatedEstimatedWasteCost;
  final SimulatedRiskChange simulatedRiskChange;
  final int reorderUrgencyScore;
  final int wasteRiskScore;
  final RecommendedAction recommendedAction;

  const SimulationResponse({
    required this.itemId,
    required this.simulatedOrderQty,
    required this.simulatedCashOutlay,
    required this.simulatedCoverageDays,
    required this.simulatedInventoryValue,
    required this.simulatedEstimatedWasteCost,
    required this.simulatedRiskChange,
    required this.reorderUrgencyScore,
    required this.wasteRiskScore,
    required this.recommendedAction,
  });

  factory SimulationResponse.fromJson(Map<String, dynamic> json) => SimulationResponse(
        itemId: _requireInt(json, 'item_id'),
        simulatedOrderQty: _requireDouble(json, 'simulated_order_qty'),
        simulatedCashOutlay: _requireDouble(json, 'simulated_cash_outlay'),
        simulatedCoverageDays: _requireDouble(json, 'simulated_coverage_days'),
        simulatedInventoryValue: _requireDouble(json, 'simulated_inventory_value'),
        simulatedEstimatedWasteCost: _requireDouble(json, 'simulated_estimated_waste_cost'),
        simulatedRiskChange: simulatedRiskChangeFromJson(_requireString(json, 'simulated_risk_change')),
        reorderUrgencyScore: _requireInt(json, 'reorder_urgency_score'),
        wasteRiskScore: _requireInt(json, 'waste_risk_score'),
        recommendedAction: recommendedActionFromJson(_requireString(json, 'recommended_action')),
      );

  Map<String, dynamic> toJson() => {
        'item_id': itemId,
        'simulated_order_qty': simulatedOrderQty,
        'simulated_cash_outlay': simulatedCashOutlay,
        'simulated_coverage_days': simulatedCoverageDays,
        'simulated_inventory_value': simulatedInventoryValue,
        'simulated_estimated_waste_cost': simulatedEstimatedWasteCost,
        'simulated_risk_change': simulatedRiskChangeToJson(simulatedRiskChange),
        'reorder_urgency_score': reorderUrgencyScore,
        'waste_risk_score': wasteRiskScore,
        'recommended_action': recommendedActionToJson(recommendedAction),
      };
}

class ExplanationRequest {
  final double? simulatedOrderQty;
  final double? simulatedCashOutlay;
  final double? simulatedCoverageDays;
  final String? simulatedRiskChange;

  const ExplanationRequest({
    this.simulatedOrderQty,
    this.simulatedCashOutlay,
    this.simulatedCoverageDays,
    this.simulatedRiskChange,
  });

  Map<String, dynamic> toJson() => {
        'simulated_order_qty': simulatedOrderQty,
        'simulated_cash_outlay': simulatedCashOutlay,
        'simulated_coverage_days': simulatedCoverageDays,
        'simulated_risk_change': simulatedRiskChange,
      }..removeWhere((k, v) => v == null);
}

enum ExplanationSource { live, mock, fallback }

ExplanationSource explanationSourceFromJson(String v) => switch (v) {
      'live' => ExplanationSource.live,
      'mock' => ExplanationSource.mock,
      'fallback' => ExplanationSource.fallback,
      _ => throw FormatException('Unknown source: $v'),
    };

String explanationSourceToJson(ExplanationSource v) => switch (v) {
      ExplanationSource.live => 'live',
      ExplanationSource.mock => 'mock',
      ExplanationSource.fallback => 'fallback',
    };

enum PriorityLevel { high, medium, low }

PriorityLevel priorityLevelFromJson(String v) => switch (v) {
      'HIGH' => PriorityLevel.high,
      'MEDIUM' => PriorityLevel.medium,
      'LOW' => PriorityLevel.low,
      _ => throw FormatException('Unknown priority_level: $v'),
    };

String priorityLevelToJson(PriorityLevel v) => switch (v) {
      PriorityLevel.high => 'HIGH',
      PriorityLevel.medium => 'MEDIUM',
      PriorityLevel.low => 'LOW',
    };

class ExplanationResponse {
  final ExplanationSource source;
  final String itemName;
  final RecommendedAction recommendedAction;
  final PriorityLevel priorityLevel;
  final String shortReason;
  final String decisionExplanation;
  final String tradeoffSummary;
  final String suggestedNextStep;
  final String confidenceNote;
  final String warningFlag;

  const ExplanationResponse({
    required this.source,
    required this.itemName,
    required this.recommendedAction,
    required this.priorityLevel,
    required this.shortReason,
    required this.decisionExplanation,
    required this.tradeoffSummary,
    required this.suggestedNextStep,
    required this.confidenceNote,
    required this.warningFlag,
  });

  factory ExplanationResponse.fromJson(Map<String, dynamic> json) => ExplanationResponse(
        source: explanationSourceFromJson(_requireString(json, 'source')),
        itemName: _requireString(json, 'item_name'),
        recommendedAction: recommendedActionFromJson(_requireString(json, 'recommended_action')),
        priorityLevel: priorityLevelFromJson(_requireString(json, 'priority_level')),
        shortReason: _requireString(json, 'short_reason'),
        decisionExplanation: _requireString(json, 'decision_explanation'),
        tradeoffSummary: _requireString(json, 'tradeoff_summary'),
        suggestedNextStep: _requireString(json, 'suggested_next_step'),
        confidenceNote: _requireString(json, 'confidence_note'),
        warningFlag: _requireString(json, 'warning_flag'),
      );

  Map<String, dynamic> toJson() => {
        'source': explanationSourceToJson(source),
        'item_name': itemName,
        'recommended_action': recommendedActionToJson(recommendedAction),
        'priority_level': priorityLevelToJson(priorityLevel),
        'short_reason': shortReason,
        'decision_explanation': decisionExplanation,
        'tradeoff_summary': tradeoffSummary,
        'suggested_next_step': suggestedNextStep,
        'confidence_note': confidenceNote,
        'warning_flag': warningFlag,
      };
}

// Request/record shapes specified in `frontend-pages-and-fields.md`.

enum UsagePeriod { daily, weekly }

UsagePeriod usagePeriodFromJson(String v) => switch (v) {
      'daily' => UsagePeriod.daily,
      'weekly' => UsagePeriod.weekly,
      _ => throw FormatException('Unknown usage_period: $v'),
    };

String usagePeriodToJson(UsagePeriod v) => switch (v) {
      UsagePeriod.daily => 'daily',
      UsagePeriod.weekly => 'weekly',
    };

enum PerishabilityLevel { low, medium, high }

PerishabilityLevel perishabilityLevelFromJson(String v) => switch (v) {
      'Low' => PerishabilityLevel.low,
      'Medium' => PerishabilityLevel.medium,
      'High' => PerishabilityLevel.high,
      _ => throw FormatException('Unknown perishability_level: $v'),
    };

String perishabilityLevelToJson(PerishabilityLevel v) => switch (v) {
      PerishabilityLevel.low => 'Low',
      PerishabilityLevel.medium => 'Medium',
      PerishabilityLevel.high => 'High',
    };

class ManualInventoryItemInput {
  final String itemName;
  final double currentStock;
  final String unit;
  final double usageValue;
  final UsagePeriod usagePeriod;
  final int leadTimeDays;
  final double pricePerUnit;
  final double seasonalFactor;
  final PerishabilityLevel? perishabilityLevel;
  final double? recentWastePercentage;
  final String? category;
  final String? subcategory;
  final String? supplierName;
  final double? manualReorderLevel;

  const ManualInventoryItemInput({
    required this.itemName,
    required this.currentStock,
    required this.unit,
    required this.usageValue,
    required this.usagePeriod,
    required this.leadTimeDays,
    required this.pricePerUnit,
    required this.seasonalFactor,
    this.perishabilityLevel,
    this.recentWastePercentage,
    this.category,
    this.subcategory,
    this.supplierName,
    this.manualReorderLevel,
  });

  factory ManualInventoryItemInput.fromJson(Map<String, dynamic> json) => ManualInventoryItemInput(
        itemName: _requireString(json, 'item_name'),
        currentStock: _requireDouble(json, 'current_stock'),
        unit: _requireString(json, 'unit'),
        usageValue: _requireDouble(json, 'usage_value'),
        usagePeriod: usagePeriodFromJson(_requireString(json, 'usage_period')),
        leadTimeDays: _requireInt(json, 'lead_time_days'),
        pricePerUnit: _requireDouble(json, 'price_per_unit'),
        seasonalFactor: _requireDouble(json, 'seasonal_factor'),
        perishabilityLevel: _nullable<String>(json, 'perishability_level') == null
            ? null
            : perishabilityLevelFromJson(_requireString(json, 'perishability_level')),
        recentWastePercentage: (json['recent_waste_percentage'] as num?)?.toDouble(),
        category: _nullable<String>(json, 'category'),
        subcategory: _nullable<String>(json, 'subcategory'),
        supplierName: _nullable<String>(json, 'supplier_name'),
        manualReorderLevel: (json['manual_reorder_level'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toJson() => {
        'item_name': itemName,
        'current_stock': currentStock,
        'unit': unit,
        'usage_value': usageValue,
        'usage_period': usagePeriodToJson(usagePeriod),
        'lead_time_days': leadTimeDays,
        'price_per_unit': pricePerUnit,
        'seasonal_factor': seasonalFactor,
        'perishability_level': perishabilityLevel == null ? null : perishabilityLevelToJson(perishabilityLevel!),
        'recent_waste_percentage': recentWastePercentage,
        'category': category,
        'subcategory': subcategory,
        'supplier_name': supplierName,
        'manual_reorder_level': manualReorderLevel,
      }..removeWhere((k, v) => v == null);
}

class ManualAnalysisRequest {
  final List<ManualInventoryItemInput> items;
  const ManualAnalysisRequest({required this.items});
  Map<String, dynamic> toJson() => {'items': items.map((e) => e.toJson()).toList()};
}

class InventoryRecord {
  final int itemId;
  final String? lastUpdated;
  final String itemName;
  final double currentStock;
  final String unit;
  final double usageValue;
  final UsagePeriod usagePeriod;
  final int leadTimeDays;
  final double pricePerUnit;
  final double seasonalFactor;
  final String? category;
  final String? subcategory;
  final String? supplierName;
  final PerishabilityLevel? perishabilityLevel;
  final double? manualReorderLevel;
  final double? recentWastePercentage;

  final double? dailyUsage;
  final RecommendedAction? recommendedAction;

  const InventoryRecord({
    required this.itemId,
    required this.itemName,
    required this.currentStock,
    required this.unit,
    required this.usageValue,
    required this.usagePeriod,
    required this.leadTimeDays,
    required this.pricePerUnit,
    required this.seasonalFactor,
    this.category,
    this.subcategory,
    this.supplierName,
    this.perishabilityLevel,
    this.manualReorderLevel,
    this.recentWastePercentage,
    this.lastUpdated,
    this.dailyUsage,
    this.recommendedAction,
  });

  factory InventoryRecord.fromJson(Map<String, dynamic> json) => InventoryRecord(
        itemId: _requireInt(json, 'item_id'),
        lastUpdated: _nullable<String>(json, 'last_updated'),
        itemName: _requireString(json, 'item_name'),
        currentStock: _requireDouble(json, 'current_stock'),
        unit: _requireString(json, 'unit'),
        usageValue: _requireDouble(json, 'usage_value'),
        usagePeriod: usagePeriodFromJson(_requireString(json, 'usage_period')),
        leadTimeDays: _requireInt(json, 'lead_time_days'),
        pricePerUnit: _requireDouble(json, 'price_per_unit'),
        seasonalFactor: _requireDouble(json, 'seasonal_factor'),
        category: _nullable<String>(json, 'category'),
        subcategory: _nullable<String>(json, 'subcategory'),
        supplierName: _nullable<String>(json, 'supplier_name'),
        perishabilityLevel: _nullable<String>(json, 'perishability_level') == null
            ? null
            : perishabilityLevelFromJson(_requireString(json, 'perishability_level')),
        manualReorderLevel: (json['manual_reorder_level'] as num?)?.toDouble(),
        recentWastePercentage: (json['recent_waste_percentage'] as num?)?.toDouble(),
        dailyUsage: (json['daily_usage'] as num?)?.toDouble(),
        recommendedAction: _nullable<String>(json, 'recommended_action') == null
            ? null
            : recommendedActionFromJson(_requireString(json, 'recommended_action')),
      );

  Map<String, dynamic> toJson() => {
        'item_id': itemId,
        'last_updated': lastUpdated,
        'item_name': itemName,
        'current_stock': currentStock,
        'unit': unit,
        'usage_value': usageValue,
        'usage_period': usagePeriodToJson(usagePeriod),
        'lead_time_days': leadTimeDays,
        'price_per_unit': pricePerUnit,
        'seasonal_factor': seasonalFactor,
        'category': category,
        'subcategory': subcategory,
        'supplier_name': supplierName,
        'perishability_level': perishabilityLevel == null ? null : perishabilityLevelToJson(perishabilityLevel!),
        'manual_reorder_level': manualReorderLevel,
        'recent_waste_percentage': recentWastePercentage,
        'daily_usage': dailyUsage,
        'recommended_action': recommendedAction == null ? null : recommendedActionToJson(recommendedAction!),
      }..removeWhere((k, v) => v == null);
}

class InventoryRecordUpdate {
  final String? itemName;
  final double? currentStock;
  final String? unit;
  final double? usageValue;
  final UsagePeriod? usagePeriod;
  final int? leadTimeDays;
  final double? pricePerUnit;
  final double? seasonalFactor;
  final String? category;
  final String? subcategory;
  final String? supplierName;
  final PerishabilityLevel? perishabilityLevel;
  final double? manualReorderLevel;
  final double? recentWastePercentage;

  const InventoryRecordUpdate({
    this.itemName,
    this.currentStock,
    this.unit,
    this.usageValue,
    this.usagePeriod,
    this.leadTimeDays,
    this.pricePerUnit,
    this.seasonalFactor,
    this.category,
    this.subcategory,
    this.supplierName,
    this.perishabilityLevel,
    this.manualReorderLevel,
    this.recentWastePercentage,
  });

  Map<String, dynamic> toJson() => {
        'item_name': itemName,
        'current_stock': currentStock,
        'unit': unit,
        'usage_value': usageValue,
        'usage_period': usagePeriod == null ? null : usagePeriodToJson(usagePeriod!),
        'lead_time_days': leadTimeDays,
        'price_per_unit': pricePerUnit,
        'seasonal_factor': seasonalFactor,
        'category': category,
        'subcategory': subcategory,
        'supplier_name': supplierName,
        'perishability_level': perishabilityLevel == null ? null : perishabilityLevelToJson(perishabilityLevel!),
        'manual_reorder_level': manualReorderLevel,
        'recent_waste_percentage': recentWastePercentage,
      }..removeWhere((k, v) => v == null);
}

