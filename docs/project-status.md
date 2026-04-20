# StockWise Project Status

## Date
- 2026-04-20

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
- Automated tests added for services and API routes.
- Documentation updated to reflect the shared input contract, CSV compatibility behavior, and observation-history normalization.

## In Progress
- Waiting for real `ZAI_API_KEY` to verify live provider against Z.AI.
- Keeping markdown project memory current as implementation evolves.

## Blocked
- Real `ZAI_API_KEY` has not been received yet, so live Z.AI integration cannot be verified.

## Next
- Integrate the frontend against the three backend endpoints.
- Integrate the frontend entry page against both CSV upload and manual entry endpoints.
- Integrate the records page against records/read-update-delete endpoints.
- Keep `docs/` in sync whenever schema, validation, or scoring inputs change.
- When the real key arrives, verify `GLM_MODE=live` with the production request path.
- Expand tests once real Z.AI response shape is confirmed.
