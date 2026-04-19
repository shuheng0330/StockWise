# StockWise Project Status

## Date
- 2026-04-19

## Completed
- Revised PRD and SAD created.
- Backend implementation plan agreed.
- Workspace dataset confirmed and analyzed.
- FastAPI backend scaffold created under `src/stockwise_api`.
- CSV validation, metric engine, recommendation engine, simulation engine, GLM adapter, and parser/fallback implemented.
- API endpoints implemented for analysis upload, simulation, and explanation.
- Automated tests added for services and API routes.

## In Progress
- Waiting for real `ZAI_API_KEY` to verify live provider against Z.AI.
- Keeping markdown project memory current as implementation evolves.

## Blocked
- Real `ZAI_API_KEY` has not been received yet, so live Z.AI integration cannot be verified.

## Next
- Integrate the frontend against the three backend endpoints.
- When the real key arrives, verify `GLM_MODE=live` with the production request path.
- Expand tests once real Z.AI response shape is confirmed.
