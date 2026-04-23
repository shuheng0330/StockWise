# StockWise Project Status

## Date
- 2026-04-22

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
- Explanation generation now uses the in-memory analysis item first, so Supabase network issues do not break explanation responses for the current analysis.
- Frontend manual analysis requests now send the backend contract shape `{ items: [...] }`.
- Supabase migration added for `analysis_runs` and `analysis_item_results`.
- Supabase analysis snapshots now use `analysis_runs.analysis_id` as the API `analysis_id` when snapshot persistence is enabled.
- `GET /api/v1/analyses/{analysis_id}` now falls back to Supabase snapshots after an in-memory cache miss.
- Automated tests added for services and API routes.
- Documentation updated to reflect the shared input contract, CSV compatibility behavior, observation-history normalization, and Supabase persistence behavior.

## In Progress
- Waiting for real `ZAI_API_KEY` to verify live provider against Z.AI.
- Keeping markdown project memory current as implementation evolves.

## Blocked
- Real `ZAI_API_KEY` has not been received yet, so live Z.AI integration cannot be verified.

## Next
- Review and apply `supabase/migrations/202604220001_create_analysis_snapshots.sql` to the live Supabase project with `supabase db push`.
- Add authenticated `created_by` / `uploaded_by` wiring once Supabase auth/profile flow is connected.
- Verify read-after-restart behavior against the live Supabase project after migration push.
- Keep `docs/` in sync whenever schema, validation, or scoring inputs change.
- When the real key arrives, verify `GLM_MODE=live` with the production request path.
- Expand tests once real Z.AI response shape is confirmed.
