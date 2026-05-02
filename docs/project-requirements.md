# StockWise Project Requirements

## Accepted MVP Scope
- FastAPI backend for CSV ingestion, analysis, simulation, explanation, and AI Advisor chat.
- Owner-friendly manual entry flow on the same frontend entry page as CSV upload.
- Inventory records review/edit/delete flow for entered or uploaded items.
- Stable API contracts for frontend integration.
- Mock provider for offline development and live OpenAI-compatible GLM provider for explanation generation.
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
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/tradeoff-verdict`
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/explanation`
- `GET /api/v1/analyses/{analysis_id}/decision-brief`
- `POST /api/v1/analyses/{analysis_id}/ai-chat`

## Canonical Input Contract
- CSV upload and manual entry now converge into one canonical item contract before normalization and scoring.
- CSV rows and manual daily entries are treated as inventory observations.
- Source observations should be persisted before history collapse so uploaded datasets and manual daily entries remain reconstructable.
- Each new upload or manual submission should append to the authenticated user's persisted observation history and create a fresh snapshot from that full per-user history.
- Backend metrics must prefer raw historical source rows over previously calculated metrics. Previous analysis item snapshots may only be used as a coarse fallback when raw historical rows cannot be recovered.
- Analysis output collapses observations by item identity and returns one latest ranked item per item.
- Records output must also expose the uncollapsed `source_observations[]` used by that analysis so the owner can see every uploaded monthly row that feeds AI trend analysis.
- Recommendation scores must be derived only from normalized canonical fields, not from per-entry-mode parsing rules.
- Record edits also reuse the same owner-facing field set so post-upload changes stay aligned with scoring inputs.
- CSV upload requests may include optional `base_analysis_id` multipart form data. When present, the backend must use that analysis as the historical baseline instead of guessing from the latest snapshot.

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
- Date ranges are upload-order agnostic: any existing valid source date range plus any newly uploaded valid source date range must be merged and sorted by actual `Date` values before scoring.
- Re-uploading the same dataset should not duplicate identical source rows in analysis calculations or Records history.
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
- Manual analysis requests may include `base_analysis_id` to append manual entries onto a specific previous analysis history.
- The Export Analysis page should include a deterministic Business Value Snapshot that estimates monthly waste opportunity, stockout-loss opportunity, time saved, suggested StockWise plan, and value-to-price ratio from the current analysis data.
- Business Value Snapshot copy must describe these figures as estimated opportunity if recommendations are followed, not as realized savings, guaranteed ROI, revenue, profit, or sales impact.

## Supabase Persistence Contract
- CSV uploads create an `import_batches` row with the uploaded filename, file type, source row count, success count, failure count, and final status.
- CSV uploads insert every validated source row into `inventory_records` with `input_source = import` and the related `import_batch_id`.
- Manual entries insert every submitted source row into `inventory_records` with `input_source = manual` and `import_batch_id = null`.
- `record_date` must come from the canonical `date` value, defaulting to the current day only when the user did not provide a date.
- Persistent data is private per authenticated user. `items`, `suppliers`, `inventory_records`, `import_batches`, and `analysis_runs` are all user-owned.
- `items` are matched by owner-facing identity, not by name only: `owner_id`, `item_name`, `unit`, `category`, `subcategory`, and supplier identity.
- `suppliers` are created or reused by `owner_id + supplier_name` when a real supplier name is provided. Missing or normalized `Unknown` suppliers leave `supplier_id = null`.
- Upload and manual submit flows should persist the new source rows first, then rebuild the analysis from the authenticated user's full persisted observation history.
- If a persisted-history read is partial or unavailable, upload and manual submit flows should keep the previous latest analysis source observations and append the new submitted rows rather than replacing visible history with only the newest file.
- If previous raw source observations are unavailable, upload and manual submit flows may convert the previous latest item snapshots into source-like fallback observations, then append the new submitted raw rows.
- Upload and manual submit flows should retain the merged source observations on the in-memory analysis record so `/records` can show both the current item snapshots and the historical source rows that produced them.
- When Supabase persistence is enabled, `analysis_runs.analysis_id` is the API `analysis_id` returned to the frontend.
- `analysis_item_results` stores point-in-time recommendation snapshots for each ranked item in an analysis.
- `analysis_source_observations` stores the exact source observation stream used by each analysis snapshot so future uploads can append to a specific prior analysis without relying on volatile in-memory cache or imperfect `inventory_records` ownership backfills.
- `GET /api/v1/analyses/latest` returns the latest snapshot for the current authenticated user only.
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
- AI trade-off verdict returns:
  - `source`
  - `verdict` as one of `Worth it`, `Too much stock`, `Cash-heavy but safe`, `Try smaller quantity`, or `Good emergency reorder`
  - `reason`
  - `confidence_note`
  - `safety_status`
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
- AI Advisor chat returns:
  - `source`
  - `scope`
  - `answer`
  - `supporting_points[]`
  - `related_items[]` with `item_id`, `item_name`, `recommended_action`, and `reason`
  - `suggested_follow_ups[]`
  - `warning_flag`
- AI decision brief returns:
  - `source`
  - `summary`
  - `buy_today[]`
  - `buy_less[]`
  - `delay[]`
  - `estimated_impact` with `cash`, `waste`, and `shortage`
  - `top_tradeoffs[]`
  - `recommended_order[]`
  - `confidence_note`
  - `warning_flag`
  - `safety_status`
- Records endpoint returns:
  - `analysis_id`
  - `dataset_summary`
  - `kpi_summary`
  - `items[]` with owner-facing editable fields, including `subcategory`, and current recommended action for the latest grouped item
  - `source_observations[]` with every uploaded/manual source row used by this analysis, including `date`, item identity, stock, usage, supplier, seasonality, and waste inputs
- Record update returns:
  - updated item record with owner-facing fields plus current `recommended_action`

## Current GLM Mode
- Local development can use `mock`.
- The current configured live provider uses `GLM_MODE=live`, `ZAI_BASE_URL=https://api.ilmu.ai/v1/chat/completions`, and `ZAI_MODEL=ilmu-glm-5.1`.
- The ILMU live provider defaults to non-streaming responses because its streaming chunks may be empty even when the non-streaming chat completion returns usable JSON.
- Live explanation generation has been verified through the production request path; invalid or unavailable model output still falls back to deterministic explanations.
- The same provider path now also supports AI decision briefs, AI Advisor chat, and simulation trade-off verdicts with structured JSON responses and deterministic fallback.

## GLM Centrality and Decision Brief
- Deterministic scoring produces grounded evidence: metrics, risks, action labels, and impact estimates.
- Z.AI GLM is the decision intelligence layer that turns this evidence into an owner-ready operating plan.
- The Business Value Snapshot is intentionally deterministic so the economic-impact numbers remain transparent and auditable; GLM remains responsible for context-aware reasoning, explanation, and trade-off interpretation.
- The dashboard loads deterministic analysis first, then fetches the AI Decision Brief asynchronously so GLM latency or failure does not block KPI cards, filters, AI Advisor, or the item table.
- The AI Decision Brief explains what to buy today, what to buy less, what can be delayed, estimated cash/waste/shortage impact, top trade-offs, and recommended order of action.
- AI Advisor and Decision Brief prompts receive compact historical summaries from deterministic backend calculation, not raw CSV rows.
- The Simulation page also asks GLM for a compact trade-off verdict after server-computed simulation metrics are available, so owners get an immediate qualitative interpretation without treating AI as the numeric source of truth.
- If the GLM component is removed, StockWise can still show raw scores and rule labels, but it loses dashboard-level contextual reasoning, cross-item strategy, and owner-friendly decision synthesis.

## Fallback and Failure Behavior
- GLM outputs for explanations, AI Advisor chat, AI decision briefs, and simulation trade-off verdicts are parsed as JSON and validated before being returned to the user.
- Hallucinated or unusable decision brief responses are rejected when they contain invalid JSON, missing fields, unknown item IDs, mismatched item names/actions, unsupported revenue/profit/sales claims, or overlong text.
- Trade-off verdict responses are rejected when they contain invalid JSON, unsupported verdict labels, unsupported revenue/profit/sales claims, or overlong text.
- The backend retries once with stricter JSON-only context after a validation failure.
- If the retry fails or the provider is unavailable, the backend returns deterministic fallback AI payloads with `source = fallback` and `safety_status = fallback_used` where applicable.
- The frontend keeps deterministic analysis visible and shows a visible safety state with a Review Records path so the owner can inspect or correct source data before ordering.

## User-Visible Success Criteria
- Upload the provided inventory CSV and receive ranked actions and KPI summaries.
- Upload the provided 100-day inventory CSV and see the dashboard collapse it into the latest item-level recommendations instead of duplicate daily rows.
- Upload monthly stock CSV files over time and see Records retain every monthly source row while Dashboard/Records latest-snapshot tables continue to show one current row per item.
- Large uploads must still create durable analysis snapshots and exact source-observation snapshots even when the longer `inventory_records` persistence path exceeds the configured response timeout.
- The Supabase analysis snapshot write is required and should wait for completion; the short optional timeout is only for long observation-import persistence.
- Enter inventory manually without needing technical CSV fields like `Waste_Percentage` or `Reorder_Level`.
- Enter repeated manual daily records for the same item and have them contribute to trend-aware analysis.
- Upload a CSV, then add manual records later, and see the next dashboard/records view reflect the merged current history for that same authenticated user instead of replacing the earlier data.
- Receive the same validation rules and scoring behavior whether data comes from CSV upload or manual entry.
- Provide the score-driving inputs directly instead of relying on backend defaults for pricing, seasonality, or waste signals.
- Review, edit, and delete records before relying on the decision dashboard.
- Simulate reorder quantity changes for a chosen item.
- See an AI trade-off verdict automatically after simulation, while keeping the server-computed simulation metrics visible as the numeric source of truth.
- Receive a safe explanation payload even when model output is invalid.
- Keep deterministic rankings visible when explanation generation fails.
- Ask the AI Advisor grounded questions about the current analysis, including what to buy today, which items to delay, and why a category looks risky.
- See an AI Decision Brief load independently after the dashboard appears, including safe fallback status when model output is unavailable or rejected.
- From the simulation flow, hand off a simulated result back into the dashboard AI Advisor and ask what changed after the scenario.
- Open Export Analysis and see a report-ready Business Value Snapshot with estimated monthly opportunity, suggested plan, and value-to-price ratio without cluttering the dashboard.
