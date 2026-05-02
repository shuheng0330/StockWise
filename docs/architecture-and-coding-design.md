# StockWise Architecture and Coding Design

## Module Map
- `src/stockwise_api/api`
- `src/stockwise_api/schemas`
- `src/stockwise_api/services`
- `src/stockwise_api/store`

## Concrete Files
- `src/stockwise_api/api/app.py`
- `src/stockwise_api/contracts.py`
- `src/stockwise_api/schemas.py`
- `src/stockwise_api/store.py`
- `src/stockwise_api/services/manual_input.py`
- `src/stockwise_api/services/validation.py`
- `src/stockwise_api/services/metrics.py`
- `src/stockwise_api/services/recommendations.py`
- `src/stockwise_api/services/simulation.py`
- `src/stockwise_api/services/glm.py`
- `src/stockwise_api/services/parsing.py`

## Planned Contracts
- Upload analysis endpoint accepts a CSV file plus optional `base_analysis_id`, then returns dataset summary, KPI summary, and item list.
- Manual analysis endpoint accepts owner-friendly fields plus optional `base_analysis_id`, then returns the same analysis payload as CSV upload.
- Records endpoint returns editable owner-facing latest item records plus the uncollapsed source observations used by the current analysis.
- Record patch endpoint updates one item and returns the updated record.
- Record delete endpoint removes one item and returns the remaining record set.
- Simulation endpoint returns scenario metrics and updated action.
- Trade-off verdict endpoint returns `live`, `mock`, or `fallback` compact GLM interpretation for a server-computed simulation.
- Explanation endpoint returns `live`, `mock`, or `fallback` explanation payload.
- Decision brief endpoint returns `live`, `mock`, or `fallback` dashboard-level action plan payload.
- AI chat endpoint returns `live`, `mock`, or `fallback` chat cards scoped to the current analysis or a simulation handoff.

## Canonical Input Flow
- `src/stockwise_api/contracts.py` defines the canonical item contract shared by manual entry, CSV ingestion, and record updates.
- `src/stockwise_api/services/validation.py` maps raw CSV headers into canonical field names, validates required and optional fields, and produces a canonical payload.
- `src/stockwise_api/services/manual_input.py` normalizes canonical payloads into the internal analysis shape used by metrics and recommendations.
- CSV uploads and manual analysis requests are treated as observation streams before scoring.
- Validated source observations are offered to Supabase persistence before they are collapsed into latest item-level analysis rows.
- Observation streams collapse into one latest internal item per item identity before the recommendation engine runs.
- The API keeps the merged source observation stream on the in-memory analysis record so `/records` can display historical uploads separately from the latest recommendation snapshot.
- New CSV and manual create flows build an explicit baseline from previous latest raw source observations plus the newly submitted rows, then let a complete Supabase persisted history replace that baseline only when it is at least as complete.
- If previous raw source observations are missing, create flows convert previous latest item snapshots into source-like fallback observations before appending the new raw rows.
- Both entry modes must reach the recommendation engine through this same validation and normalization flow.
- Required score-driving inputs are enforced at the canonical schema layer so the recommendation engine does not depend on fallback guesses for price or seasonality.

## CSV Header Mapping
- Owner-friendly CSV headers map directly to canonical fields.
- Legacy dataset headers are supported through alias mapping.
- `Daily_Usage` is treated as canonical `usage_value` with inferred `usage_period = daily`.
- `Reorder_Level` is treated as canonical `manual_reorder_level`.
- `Waste_Percentage` is treated as canonical `recent_waste_percentage`.
- Either `perishability_level` or `recent_waste_percentage` must be present for each item as the waste signal used to derive `waste_percentage`.
- Uploaded `Date` values drive dataset summary date ranges when present.

## Manual Input Normalization
- `usage_value + usage_period` are normalized into `daily_usage`
- required `seasonal_factor` is passed through from validated input
- required `price_per_unit` is passed through from validated input
- default `category = "Uncategorized"`
- default `supplier_name = "Unknown"`
- default `reorder_level = max(daily_usage * lead_time_days, daily_usage)`
- `waste_percentage` is inferred from `perishability_level`
  - `low -> 1.5`
  - `medium -> 3.0`
  - `high -> 4.5`
- if `recent_waste_percentage` is provided, it overrides the perishability-based default
- if `manual_reorder_level` is provided, it overrides the system-generated reorder level
- `subcategory` is preserved from canonical input when present, otherwise it falls back to `category` and then `"General"`
- single-entry manual submissions still produce a valid latest item with `avg_usage_7d = daily_usage` and `trend_direction = stable`

## Observation History Normalization
- `normalize_item_history` first reuses the manual normalization path for every observation.
- Observations with a source `item_id` are grouped by that ID.
- Observations without a source `item_id` are grouped by `item_name`, `unit`, `category`, and `subcategory` so owner-friendly manual records can build history over time.
- Each group is sorted by `date` and original observation order.
- The latest observation in each group supplies the current snapshot used for scoring.
- Upload order does not determine chronology; the uploaded `Date` values determine the merged date range and the latest row per item.
- Exact duplicate source observations are removed from the assembled stream before normalization so re-uploading the same CSV does not double-count history.
- The grouped output preserves the first stable `item_id` for records, simulation, and explanation endpoints.
- `avg_usage_7d` is computed from up to the seven most recent observations in the group.
- `trend_direction` is computed from first-vs-latest usage in that recent window.
- `/records` returns both `items[]` for the latest editable snapshots and `source_observations[]` for all historical source rows feeding those snapshots.

## Supabase Persistence Flow
- `src/stockwise_api/store.py` contains `SupabaseAnalysisStore.persist_observations`.
- `POST /api/v1/analyses` passes validated CSV rows to `persist_observations` with `source_type = import`, `file_name`, and `file_type = csv`.
- `POST /api/v1/manual-analyses` passes submitted manual rows to `persist_observations` with `source_type = manual`.
- Dashboard and Data Entry navigation carry the current analysis id as `baseAnalysisId`; the frontend sends it as `base_analysis_id` so the backend can append a new upload to the intended historical snapshot instead of guessing from whichever snapshot Supabase reports as latest.
- API create routes resolve the authenticated Supabase user from the bearer token before any user-scoped read or write.
- `inventory_records.created_by`, `import_batches.uploaded_by`, and `analysis_runs.created_by` are the authoritative per-user ownership fields.
- Persistence normalizes each source observation through the same canonical manual normalization path used by analysis.
- Import persistence creates one `import_batches` row before row inserts and updates it to `success`, `partial`, or `failed`.
- Each persisted observation creates one `inventory_records` row; historical CSVs therefore store all source rows, not just grouped latest rows.
- Import row persistence failures are recorded in `import_row_errors` when an import batch exists.
- `items.owner_id` and `suppliers.owner_id` scope reference data to one authenticated user.
- Suppliers are matched or inserted by `supplier_name + owner_id`; normalized missing or `Unknown` suppliers remain nullable.
- Items are matched by `owner_id + item_name + unit + category + subcategory + supplier_id` to avoid merging different owner-facing items with the same name across accounts.
- Supabase writes are best-effort for the MVP. Analysis responses are still generated from the deterministic in-memory analysis record if persistence fails.

## Supabase Analysis Snapshot Flow
- Migration file: `supabase/migrations/202604220001_create_analysis_snapshots.sql`.
- Ownership migration file: `supabase/migrations/202604240001_add_user_ownership_to_items_and_suppliers.sql`.
- `analysis_runs` stores one row per analysis and owns the API-level `analysis_id` when Supabase snapshots are enabled.
- `analysis_item_results` stores the ranked point-in-time recommendation rows for each analysis.
- `analysis_source_observations` stores the exact raw/canonical source observation stream used for that analysis, keyed by `analysis_id` and `row_number`.
- `analysis_item_results.app_item_id` preserves the current frontend/API integer item ID used by records, simulation, and explanation routes.
- `analysis_item_results.item_id` and `latest_record_id` link to Supabase `items` and `inventory_records` when observation persistence returns those IDs; both remain nullable for offline/test paths.
- API create endpoints persist the submitted observations, reload the authenticated user's full persisted observation history, collapse and rank that merged history, then persist a new analysis snapshot and use the returned `analysis_id` in the in-memory cache.
- If the general Supabase user-history read is incomplete, API create endpoints recover the exact previous analysis source observations from `analysis_source_observations` before appending new validated rows and creating the fresh snapshot.
- Analysis snapshot persistence is attempted even when the long-running inventory observation persistence path times out, so `analysis_runs` and `analysis_source_observations` do not disappear just because `import_batches` continues in the background.
- `create_analysis_snapshot` runs outside `_run_optional_supabase_operation`; the upload response should wait for this critical durable snapshot and use the Supabase `analysis_id` when it succeeds.
- The snapshot path emits `stockwise.analysis_snapshot.start`, `stockwise.analysis_snapshot.success`, `stockwise.analysis_snapshot.failure`, and `stockwise.analysis_snapshot.skipped` log events for production diagnosis.
- `/health` reports `supabase_store_ready`, `history_snapshot_table`, `snapshot_write_mode`, and the configured Supabase timeout so a deployed backend can be checked before upload tests.
- Source observation snapshots are inserted in chunks instead of one row at a time to keep 1,000+ row histories within the production request budget.
- `GET /api/v1/analyses/latest` resolves the latest snapshot for the authenticated user only.
- `GET /api/v1/analyses/{analysis_id}` reads from the in-memory cache first, then falls back to `SupabaseAnalysisStore.get`, enforcing snapshot ownership when a user ID is present.
- Supabase fallback reads copy `source_observations` into the in-memory cache along with item snapshots so follow-up uploads keep using raw historical rows.
- To apply schema changes to the live Supabase project, run `supabase link --project-ref fujcmskmahkvyulzxvuy` and `supabase db push` after reviewing the migration.

## Metrics and Thresholds
- `days_of_cover`
- `inventory_value`
- `estimated_waste_cost`
- `lead_time_demand`
- `stock_gap_to_lead_demand`
- `avg_usage_7d`
- `trend_direction`
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
- Live provider requests use `response_format = {"type": "json_object"}`, `thinking = {"type": "disabled"}`, and a bounded output token budget so GLM responses land in `message.content` as parseable JSON.
- Live provider streaming is controlled by `ZAI_STREAM=true|false`. The ILMU endpoint defaults to non-streaming because its streamed chunks may contain no visible `content`, while non-streaming returns the JSON payload through the normal chat-completions message body.
- AI decision brief uses a dashboard-level prompt with dataset summary, KPI summary, top ranked items, and deterministic impact notes. It returns `summary`, `buy_today`, `buy_less`, `delay`, `estimated_impact`, `top_tradeoffs`, `recommended_order`, `confidence_note`, and `warning_flag`.
- AI Advisor chat uses the same live provider path but a separate inventory-Advisor prompt and a compact analysis summary instead of the explanation-only item contract.
- AI decision brief and AI Advisor prompt contexts include compact historical summaries such as date range, source observation count, item observation count, latest observation date, average usage, and trend direction. Raw CSV/source rows are not sent to the model.
- AI trade-off verdict uses a compact simulation prompt with current item metrics and server-computed simulation metrics. It returns `verdict`, `reason`, and `confidence_note`, and the verdict must be one of the allowed owner-facing labels.

## Parser and Fallback Flow
- Parse JSON
- Validate required keys and enums
- Check item match and unsupported claims
- Retry once on malformed response
- Fall back to deterministic template if still invalid
- Decision brief validation also rejects unknown item IDs, mismatched item names/actions, unsupported revenue/profit/sales claims, and overlong text before returning content to the frontend.
- Decision brief fallback returns `source = fallback` and `safety_status = fallback_used`, with a user-visible warning to review records before ordering.
- AI Advisor chat follows the same pattern with its own schema validation for `scope`, `supporting_points`, `related_items`, and `suggested_follow_ups`.
- Trade-off verdict validation rejects invalid verdict labels, malformed JSON, unsupported revenue/profit/sales claims, and overlong text, then falls back to a deterministic verdict based on the same simulation metrics.

## Runtime Notes
- App factory: `stockwise_api.api.app:create_app`
- `create_app` accepts an injectable `supabase_store` for tests and local integration seams.
- The frontend computes the Business Value Snapshot client-side from the existing `AnalysisResponse`; no backend endpoint or GLM call is required for these arithmetic estimates.
- Business Value Snapshot formulas use current waste exposure, stockout shortfall value, item count, and a four-review-cycles-per-month assumption to produce report-ready opportunity estimates on the Export page.
- Default provider mode: `mock`
- Live provider fails fast at startup if `GLM_MODE=live` and `ZAI_API_KEY` is missing
- The current live configuration uses the ILMU OpenAI-compatible chat-completions endpoint with `ZAI_BASE_URL=https://api.ilmu.ai/v1/chat/completions` and `ZAI_MODEL=ilmu-glm-5.1`.
- `POST /api/v1/analyses/{analysis_id}/ai-chat` loads the authenticated user's current analysis snapshot, trims ranked items into a compact prompt context, and optionally adds one server-computed simulation comparison when `simulation_context` is provided.
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/tradeoff-verdict` recomputes the simulation server-side from `simulated_order_qty`, then asks GLM for a concise trade-off verdict without allowing it to invent numeric outcomes.
- `GET /api/v1/analyses/{analysis_id}/decision-brief` loads the current analysis snapshot and generates a dashboard-level GLM brief without blocking analysis creation or dashboard rendering.
- The frontend should fetch the decision brief in parallel after loading the dashboard route; KPI cards, filters, Advisor, and the item table remain visible while the brief is pending or falls back.
- Off-topic AI chat requests are refused deterministically instead of being forwarded to the model.
- CSV uploads preserve source `item_id` values when present and collapse repeated historical observations into one latest item per source item.
- Manual analysis requests can include repeated dated entries for the same owner-facing item; those entries collapse into one latest item with trend-aware metrics.
- `dataset_summary.row_count` reports source observations; `dataset_summary.item_count` reports grouped analyzed items.
- Record edits and deletions trigger a full re-rank and KPI recomputation for the affected analysis
- Record payloads expose `price_per_unit` and `seasonal_factor` as non-null score-driving inputs
- Records pages render source upload history separately from latest item snapshots so repeated monthly CSV uploads remain visible to the owner.

## Environment Variables
- `STOCKWISE_SUPABASE_ENABLED=true|false`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GLM_MODE=mock|live`
- `ZAI_API_KEY`
- `ZAI_BASE_URL`
- `ZAI_MODEL`
- `ZAI_STREAM=true|false`
