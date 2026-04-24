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
- `items.owner_id` and `suppliers.owner_id` are now part of the source-of-truth persistence design so same-named reference data does not collide across accounts.
- `GET /api/v1/analyses/latest` is now defined as latest-for-current-user instead of a global latest snapshot.
- Explanation generation now uses the in-memory analysis item first, so Supabase network issues do not break explanation responses for the current analysis.
- Frontend manual analysis requests now send the backend contract shape `{ items: [...] }`.
- Supabase migration added for `analysis_runs` and `analysis_item_results`.
- Supabase analysis snapshots now use `analysis_runs.analysis_id` as the API `analysis_id` when snapshot persistence is enabled.
- `GET /api/v1/analyses/{analysis_id}` now falls back to Supabase snapshots after an in-memory cache miss.
- Live GLM explanation generation verified through the configured ILMU OpenAI-compatible endpoint.
- Live provider requests now use JSON mode, disable thinking, and allocate enough output tokens for the required explanation contract.
- AI Inventory Copilot chat implemented on the dashboard with structured responses, simulation handoff, and deterministic fallback.
- Automated tests added for services and API routes.
- Documentation updated to reflect the shared input contract, CSV compatibility behavior, observation-history normalization, and Supabase persistence behavior.

## In Progress
- Keeping markdown project memory current as implementation evolves.

## Blocked
- None currently documented.

## Next
- Review and apply `supabase/migrations/202604220001_create_analysis_snapshots.sql` and `supabase/migrations/202604240001_add_user_ownership_to_items_and_suppliers.sql` to the live Supabase project with `supabase db push`.
- Verify read-after-restart behavior against the live Supabase project after migration push.
- Keep `docs/` in sync whenever schema, validation, or scoring inputs change.
- Add a lightweight runtime status endpoint or settings display for `mock`, `live`, and `fallback` explanation state.
- Expand integration smoke coverage around live-compatible provider response shape without requiring network in the default test suite.
- Decide whether record edit/delete should stay snapshot-local or later become true persisted-observation mutation.
