# StockWise Project Status

## Date
- 2026-04-24

## Completed
- Revised PRD and SAD created.
- Backend implementation plan agreed.
- Workspace dataset confirmed and analyzed.
- FastAPI backend scaffold created under `src/stockwise_api`.
- CSV validation, metric engine, recommendation engine, simulation engine, GLM adapter, and parser/fallback implemented.
- API endpoints implemented for analysis upload, simulation, and explanation.
- Owner-friendly manual entry backend flow implemented.
- Inventory records backend flow implemented for read, update, and delete.
- Canonical input contract added so CSV upload, manual entry, and record edits share the same field definitions and validation rules.
- Legacy dataset CSV headers now map into the canonical owner-facing schema before normalization and scoring.
- Record payloads now preserve `subcategory`, and CSV uploads preserve provided `item_id` values.
- Score-driving owner inputs are now stricter: `price_per_unit` and `seasonal_factor` are required, and each item must provide either `perishability_level` or `recent_waste_percentage`.
- Documentation now reflects the frontend guidance to collect these score-driving inputs with guided choices instead of backend defaults.
- Frontend page and field requirements documented in `docs/frontend-pages-and-fields.md`.
- Historical CSV uploads now collapse repeated observations into latest item-level recommendations with real recent usage averages and trend direction.
- Manual analysis requests now support repeated dated entries for the same owner-facing item, preserving the friendly daily-entry flow while building trend-aware history.
- Supabase persistence now stores source observations before analysis collapse, so historical CSV uploads persist every validated row in `inventory_records`.
- CSV imports now create/update `import_batches`; row-level persistence failures can be written to `import_row_errors`.
- Manual observations now persist as `input_source = manual` without an import batch, while CSV observations persist as `input_source = import`.
- Supabase item matching now uses owner-facing identity fields instead of item name only.
- Authenticated `created_by` / `uploaded_by` wiring is now connected for user-owned writes when bearer-token auth is enabled.
- New uploads and manual submissions now append to the authenticated user's persisted observation history and create a fresh merged snapshot from that full per-user history.
- Upload and manual submit flows now protect against partial Supabase history reads by falling back to the previous latest analysis source observations plus the newly submitted rows, preventing monthly CSV uploads from replacing older visible source history.
- Upload and manual submit flows now use previous raw source rows first, fall back to previous item snapshots only when raw rows are unavailable, and merge arbitrary uploaded date ranges by actual source `Date` before scoring.
- Exact duplicate source rows are now deduplicated before analysis so re-uploading the same CSV does not double-count observations.
- Dashboard/Data Entry navigation now carries the current analysis as `baseAnalysisId`, and CSV/manual submissions forward it as `base_analysis_id` so new data appends to the intended prior analysis history, not an unrelated latest snapshot.
- Supabase analysis snapshots now persist their exact source observation stream in `analysis_source_observations`, fixing the durable-history root cause instead of relying on in-memory cache or latest-analysis guessing.
- Upload flows now still attempt the Supabase analysis snapshot when inventory observation persistence times out, fixing the case where fresh `import_batches` existed but no matching `analysis_runs` or `analysis_source_observations` were written.
- The critical analysis snapshot write no longer uses the short optional Supabase timeout, and production diagnostics now include `stockwise.analysis_snapshot.*` log events plus `/health` snapshot metadata.
- Supabase-loaded analysis snapshots now retain `source_observations` in the in-memory cache, preventing later uploads from degrading to latest item snapshots after a dashboard/read path warms the cache.
- Supabase read recovery now rebuilds current item snapshots from `analysis_source_observations` when `analysis_item_results` is incomplete, fixing dashboard count mismatches such as 8 KPI items versus 10 source snapshots.
- Source observation snapshot rows are inserted in chunks to make large history snapshots practical for production uploads.
- AI Decision Brief and AI Advisor contexts now receive compact historical summaries instead of raw source rows.
- `items.owner_id` and `suppliers.owner_id` are now part of the source-of-truth persistence design so same-named reference data does not collide across accounts.
- `GET /api/v1/analyses/latest` is now defined as latest-for-current-user instead of a global latest snapshot.
- Explanation generation now uses the in-memory analysis item first, so Supabase network issues do not break explanation responses for the current analysis.
- Frontend manual analysis requests now send the backend contract shape `{ items: [...] }`.
- Supabase migration added for `analysis_runs` and `analysis_item_results`.
- Supabase analysis snapshots now use `analysis_runs.analysis_id` as the API `analysis_id` when snapshot persistence is enabled.
- `GET /api/v1/analyses/{analysis_id}` now falls back to Supabase snapshots after an in-memory cache miss.
- Live GLM explanation generation verified through the configured ILMU OpenAI-compatible endpoint.
- Live provider requests now use JSON mode, disable thinking, and allocate enough output tokens for the required explanation contract.
- AI Inventory Advisor chat implemented on the dashboard with structured responses, simulation handoff, and deterministic fallback.
- AI Advisor warning labels now suppress placeholder model values such as `none`, `null`, and `n/a` instead of showing them as yellow warning callouts.
- AI Decision Brief confidence notes now reinforce that recommendations are grounded in history plus current records when `row_count` shows historical source observations.
- AI Trade-off Verdict implemented for the Simulation page, with server-computed simulation metrics, compact GLM interpretation, strict parser validation, deterministic fallback, and inline frontend rendering.
- Business Value Snapshot added to the Export Analysis plan and frontend implementation as a deterministic report-ready estimate for monthly waste opportunity, stockout-loss opportunity, time saved, suggested StockWise plan, and value-to-price ratio.
- Automated tests added for services and API routes.
- Documentation updated to reflect the shared input contract, CSV compatibility behavior, observation-history normalization, Supabase persistence behavior, and simulation trade-off verdict behavior.

## In Progress
- Keeping markdown project memory current as implementation evolves.

## Blocked
- None currently documented.

## Next
- Redeploy the backend after the required snapshot-write fix, then confirm `/health` shows `snapshot_write_mode = required` before testing uploads.
- Verify read-after-restart behavior against the live Supabase project after backend redeploy.
- Keep `docs/` in sync whenever schema, validation, or scoring inputs change.
- Add a lightweight runtime status endpoint or settings display for `mock`, `live`, and `fallback` explanation state.
- Expand integration smoke coverage around live-compatible provider response shape without requiring network in the default test suite.
- Capture final QA evidence for the AI Trade-off Verdict path: parser/API fallback tests, frontend rendering test, and manual simulation screenshot.
- Capture final QA evidence for the Export Analysis Business Value Snapshot, including focused frontend tests and production build output.
- Decide whether record edit/delete should stay snapshot-local or later become true persisted-observation mutation.
- Audit existing production `inventory_records.created_by` backfill so older imported rows are user-owned and available through the persisted history query.
