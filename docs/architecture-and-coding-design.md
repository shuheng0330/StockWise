# StockWise Architecture and Coding Design

## Module Map
- `src/stockwise_api/api`
- `src/stockwise_api/schemas`
- `src/stockwise_api/services`
- `src/stockwise_api/store`

## Concrete Files
- `src/stockwise_api/api/app.py`
- `src/stockwise_api/schemas.py`
- `src/stockwise_api/store.py`
- `src/stockwise_api/services/validation.py`
- `src/stockwise_api/services/metrics.py`
- `src/stockwise_api/services/recommendations.py`
- `src/stockwise_api/services/simulation.py`
- `src/stockwise_api/services/glm.py`
- `src/stockwise_api/services/parsing.py`

## Planned Contracts
- Upload analysis endpoint returns dataset summary, KPI summary, and item list.
- Simulation endpoint returns scenario metrics and updated action.
- Explanation endpoint returns `live`, `mock`, or `fallback` explanation payload.

## Metrics and Thresholds
- `days_of_cover`
- `inventory_value`
- `estimated_waste_cost`
- `lead_time_demand`
- `stock_gap_to_lead_demand`
- `reorder_urgency_score`
- `waste_risk_score`

## Scoring Formulas
- `reorder_urgency_score`
  - `40*lead_time_gap_ratio`
  - `20*reorder_gap_ratio`
  - `20*usage_pressure`
  - `10*lead_time_pressure`
  - `10*seasonal_pressure`
- `waste_risk_score`
  - `45*waste_pressure`
  - `35*value_pressure`
  - `20*over_coverage_ratio`

## Action Rules
- `RESTOCK_NOW` if `stock_gap_to_lead_demand < 0` or urgency >= 70
- `BUY_LESS` if waste risk >= 70 and urgency < 70
- `DELAY_PURCHASE` if urgency < 40, waste risk < 60, and `days_of_cover > lead_time * seasonal_factor`
- `MONITOR_CLOSELY` otherwise

## Prompt Contract
- System prompt is constrained and JSON-only.
- Only structured item context is sent to the provider.
- Context includes item identity, current metrics, derived metrics, recent context, and optional simulation context.

## Parser and Fallback Flow
- Parse JSON
- Validate required keys and enums
- Check item match and unsupported claims
- Retry once on malformed response
- Fall back to deterministic template if still invalid

## Runtime Notes
- App factory: `stockwise_api.api.app:create_app`
- Default provider mode: `mock`
- Live provider fails fast at startup if `GLM_MODE=live` and `ZAI_API_KEY` is missing

## Environment Variables
- `GLM_MODE=mock|live`
- `ZAI_API_KEY`
- `ZAI_BASE_URL`
- `ZAI_MODEL`
