import { AnalysisResponse } from '@/types';

const REVIEW_CYCLES_PER_MONTH = 4;
const MANUAL_REVIEW_MINUTES_PER_ITEM = 2;
const MIN_MANUAL_REVIEW_MINUTES = 15;

export type StockWisePlanName = 'Free' | 'Starter' | 'Pro';

export interface SuggestedStockWisePlan {
  name: StockWisePlanName;
  monthlyPrice: number;
  rationale: string;
}

export interface BusinessValueSnapshot {
  monthlyWasteAvoided: number;
  monthlyStockoutLossAvoided: number;
  monthlyOpportunityValue: number;
  monthlyTimeSavedHours: number;
  suggestedPlan: SuggestedStockWisePlan;
  valueToCostRatio: number | null;
  assumptions: string[];
}

function roundCurrency(value: number) {
  return Math.round(value * 100) / 100;
}

function roundOneDecimal(value: number) {
  return Math.round(value * 10) / 10;
}

function positiveNumber(value: number | null | undefined) {
  return Number.isFinite(value) && value && value > 0 ? value : 0;
}

function choosePlan(itemCount: number, monthlyOpportunityValue: number): SuggestedStockWisePlan {
  if (monthlyOpportunityValue <= 0) {
    return {
      name: 'Free',
      monthlyPrice: 0,
      rationale: 'No measurable value exposure was detected in this analysis.',
    };
  }

  if (itemCount > 25 || monthlyOpportunityValue >= 1000) {
    return {
      name: 'Pro',
      monthlyPrice: 99,
      rationale: 'Best fit for larger catalogues or higher-value inventory exposure.',
    };
  }

  return {
    name: 'Starter',
    monthlyPrice: 39,
    rationale: 'Best fit for a small catalogue with measurable inventory exposure.',
  };
}

export function buildBusinessValueSnapshot(analysis: AnalysisResponse): BusinessValueSnapshot {
  const wasteExposurePerCycle = analysis.items.reduce((total, item) => {
    const isWasteOpportunity = item.recommended_action === 'BUY_LESS' || item.waste_risk_score >= 70;
    return isWasteOpportunity ? total + positiveNumber(item.estimated_waste_cost) : total;
  }, 0);

  const stockoutExposurePerCycle = analysis.items.reduce((total, item) => {
    const shortfallUnits = Math.abs(Math.min(item.stock_gap_to_lead_demand, 0));
    const isStockoutOpportunity = item.recommended_action === 'RESTOCK_NOW' || shortfallUnits > 0;
    return isStockoutOpportunity ? total + shortfallUnits * positiveNumber(item.price_per_unit) : total;
  }, 0);

  const monthlyWasteAvoided = roundCurrency(wasteExposurePerCycle * REVIEW_CYCLES_PER_MONTH);
  const monthlyStockoutLossAvoided = roundCurrency(stockoutExposurePerCycle * REVIEW_CYCLES_PER_MONTH);
  const monthlyOpportunityValue = roundCurrency(monthlyWasteAvoided + monthlyStockoutLossAvoided);
  const itemCount = analysis.kpi_summary.item_count || analysis.items.length;
  const monthlyTimeSavedHours = roundOneDecimal(
    (Math.max(MIN_MANUAL_REVIEW_MINUTES, itemCount * MANUAL_REVIEW_MINUTES_PER_ITEM) *
      REVIEW_CYCLES_PER_MONTH) /
      60
  );
  const suggestedPlan = choosePlan(itemCount, monthlyOpportunityValue);
  const valueToCostRatio =
    suggestedPlan.monthlyPrice > 0
      ? roundOneDecimal(monthlyOpportunityValue / suggestedPlan.monthlyPrice)
      : null;

  return {
    monthlyWasteAvoided,
    monthlyStockoutLossAvoided,
    monthlyOpportunityValue,
    monthlyTimeSavedHours,
    suggestedPlan,
    valueToCostRatio,
    assumptions: [
      'Uses current analysis results as a monthly opportunity estimate.',
      'Assumes four inventory review cycles per month.',
      'Uses existing item prices as RM-equivalent decision values.',
    ],
  };
}
