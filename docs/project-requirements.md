# StockWise Project Requirements

## Accepted MVP Scope
- FastAPI backend for CSV ingestion, analysis, simulation, and explanation.
- Stable API contracts for frontend integration.
- Mock Z.AI provider until the real `ZAI_API_KEY` is available.
- In-memory analysis storage keyed by `analysis_id` for hackathon MVP speed.

## Owned Backend Responsibilities
- CSV validation layer
- Metric engine
- Recommendation engine
- Simulation engine
- GLM adapter
- Parser and fallback layer

## Endpoint Summary
- `POST /api/v1/analyses`
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/simulate`
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/explanation`

## Current Output Shape
- Analysis upload returns:
  - `analysis_id`
  - `dataset_summary`
  - `kpi_summary`
  - `items[]`
- Simulation returns:
  - `item_id`
  - `simulated_order_qty`
  - `simulated_cash_outlay`
  - `simulated_coverage_days`
  - `simulated_inventory_value`
  - `simulated_estimated_waste_cost`
  - `simulated_risk_change`
  - updated scores and `recommended_action`
- Explanation returns:
  - `source`
  - `item_name`
  - `recommended_action`
  - `priority_level`
  - `short_reason`
  - `decision_explanation`
  - `tradeoff_summary`
  - `suggested_next_step`
  - `confidence_note`
  - `warning_flag`

## Current GLM Mode
- `mock`
- `live` mode is implemented as a provider path but still blocked by missing `ZAI_API_KEY`.

## User-Visible Success Criteria
- Upload the provided inventory CSV and receive ranked actions and KPI summaries.
- Simulate reorder quantity changes for a chosen item.
- Receive a safe explanation payload even when model output is invalid.
- Keep deterministic rankings visible when explanation generation fails.
