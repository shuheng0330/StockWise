# StockWise Project Requirements

## Accepted MVP Scope
- FastAPI backend for CSV ingestion, analysis, simulation, and explanation.
- Owner-friendly manual entry flow on the same frontend entry page as CSV upload.
- Inventory records review/edit/delete flow for entered or uploaded items.
- Stable API contracts for frontend integration.
- Mock Z.AI provider until the real `ZAI_API_KEY` is available.
- Supabase persistence for source inventory observations, suppliers, items, and CSV import batches.
- In-memory analysis storage keyed by `analysis_id` remains the fast response cache for the current hackathon API flow.

## Owned Backend Responsibilities
- CSV validation layer
- Metric engine
- Recommendation engine
- Simulation engine
- GLM adapter
- Parser and fallback layer

## Endpoint Summary
- `POST /api/v1/analyses`
- `POST /api/v1/manual-analyses`
- `GET /api/v1/analyses/{analysis_id}/records`
- `PATCH /api/v1/analyses/{analysis_id}/items/{item_id}`
- `DELETE /api/v1/analyses/{analysis_id}/items/{item_id}`
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/simulate`
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/explanation`

## Canonical Input Contract
- CSV upload and manual entry now converge into one canonical item contract before normalization and scoring.
- CSV rows and manual daily entries are treated as inventory observations.
- Source observations should be persisted before history collapse so uploaded datasets and manual daily entries remain reconstructable.
- Analysis output collapses observations by item identity and returns one latest ranked item per item.
- Recommendation scores must be derived only from normalized canonical fields, not from per-entry-mode parsing rules.
- Record edits also reuse the same owner-facing field set so post-upload changes stay aligned with scoring inputs.

## Shared Required Fields
- `item_name`
- `current_stock`
- `unit`
- `usage_value`
- `usage_period`
- `lead_time_days`
- `price_per_unit`
- `seasonal_factor`

## Shared Optional Fields
- `category`
- `subcategory`
- `supplier_name`
- one waste signal:
  - `perishability_level`
  - or `recent_waste_percentage`

## Advanced Optional Fields
- `manual_reorder_level`

## CSV Compatibility
- Owner-friendly CSV headers are accepted using the same field names as manual entry.
- Legacy dataset headers are also accepted and mapped into the canonical contract:
  - `Item_Name -> item_name`
  - `Current_Stock -> current_stock`
  - `Daily_Usage -> usage_value`
  - `Lead_Time -> lead_time_days`
  - `Reorder_Level -> manual_reorder_level`
  - `Waste_Percentage -> recent_waste_percentage`
- Legacy `Daily_Usage` is interpreted as `usage_period = daily`.
- Legacy `Waste_Percentage` satisfies the required waste-signal rule even when `perishability_level` is absent.
- CSV date ranges should use uploaded `Date` values when present instead of always using the current day.
- Historical CSV uploads with repeated `item_id` values should keep `row_count` as the source observation count and set `item_count` to the number of unique analyzed items.
- Historical owner-friendly rows without `item_id` are grouped by owner-facing identity fields (`item_name`, `unit`, `category`, `subcategory`).
- For each grouped item, the latest dated observation drives current stock, price, lead-time, seasonality, waste, and scoring inputs.
- The latest grouped item should expose real `avg_usage_7d` and `trend_direction` when multiple recent observations exist.

## Frontend Guidance
- `seasonal_factor` should be presented as a guided dropdown so users can choose an estimate when unsure.
- `perishability_level` should be presented as a guided dropdown unless the user provides `recent_waste_percentage`.
- `price_per_unit` should be required with helper text that an estimate is acceptable.
- UI copy should explain that these fields directly affect the recommendation score.
- Manual analysis requests must post `{ "items": [...] }` to `POST /api/v1/manual-analyses`.

## Supabase Persistence Contract
- CSV uploads create an `import_batches` row with the uploaded filename, file type, source row count, success count, failure count, and final status.
- CSV uploads insert every validated source row into `inventory_records` with `input_source = import` and the related `import_batch_id`.
- Manual entries insert every submitted source row into `inventory_records` with `input_source = manual` and `import_batch_id = null`.
- `record_date` must come from the canonical `date` value, defaulting to the current day only when the user did not provide a date.
- `items` are matched by owner-facing identity, not by name only: `item_name`, `unit`, `category`, `subcategory`, and supplier identity.
- `suppliers` are created or reused by `supplier_name` when a real supplier name is provided. Missing or normalized `Unknown` suppliers leave `supplier_id = null`.
- When Supabase persistence is enabled, `analysis_runs.analysis_id` is the API `analysis_id` returned to the frontend.
- `analysis_item_results` stores point-in-time recommendation snapshots for each ranked item in an analysis.
- `GET /api/v1/analyses/{analysis_id}` should read from in-memory cache first and fall back to Supabase snapshot tables when needed.
- Supabase persistence failures should not break deterministic analysis responses during the MVP.

## Current Output Shape
- Analysis upload returns:
  - `analysis_id`
  - `dataset_summary`
  - `kpi_summary`
  - `items[]` with one latest ranked item per grouped inventory item
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
- Records endpoint returns:
  - `analysis_id`
  - `dataset_summary`
  - `kpi_summary`
  - `items[]` with owner-facing editable fields, including `subcategory`, and current recommended action for the latest grouped item
- Record update returns:
  - updated item record with owner-facing fields plus current `recommended_action`

## Current GLM Mode
- `mock`
- `live` mode is implemented as a provider path but still blocked by missing `ZAI_API_KEY`.

## User-Visible Success Criteria
- Upload the provided inventory CSV and receive ranked actions and KPI summaries.
- Upload the provided 100-day inventory CSV and see the dashboard collapse it into the latest item-level recommendations instead of duplicate daily rows.
- Enter inventory manually without needing technical CSV fields like `Waste_Percentage` or `Reorder_Level`.
- Enter repeated manual daily records for the same item and have them contribute to trend-aware analysis.
- Receive the same validation rules and scoring behavior whether data comes from CSV upload or manual entry.
- Provide the score-driving inputs directly instead of relying on backend defaults for pricing, seasonality, or waste signals.
- Review, edit, and delete records before relying on the decision dashboard.
- Simulate reorder quantity changes for a chosen item.
- Receive a safe explanation payload even when model output is invalid.
- Keep deterministic rankings visible when explanation generation fails.
