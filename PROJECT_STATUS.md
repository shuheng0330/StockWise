# Project Status

Canonical status is maintained in `docs/project-status.md`.

Latest update:
- Implemented historical date-range analysis so new uploads calculate from previous raw source rows plus newly uploaded rows.
- Added `base_analysis_id` handoff from frontend submissions to backend history assembly.
- Added durable Supabase snapshot source-history storage through `analysis_source_observations`.
- Fixed the timeout path so analysis snapshots and source-observation snapshots are still written when inventory-record import persistence takes too long.
- Removed the short optional timeout from the critical Supabase analysis snapshot write and added `stockwise.analysis_snapshot.*` log events plus health metadata for deployment verification.
- Fixed Supabase analysis cache hydration so loaded snapshots retain raw `source_observations` for the next upload.
- Added Supabase read recovery for incomplete `analysis_item_results`: if source observations are available, current item snapshots and KPI counts are rebuilt from the durable raw snapshot.
- Added fallback to previous latest item snapshots only when raw historical rows cannot be recovered.
- Added exact duplicate source-row deduplication for repeated CSV uploads.
- Added compact historical summaries for AI contexts without sending raw CSV rows.
- Fixed live ZAI streamed AI text collapsing spaces in the advisor and decision brief; added a regression test for whitespace-only streamed deltas.
- Fixed explanation endpoint 500s when live ZAI returns `warning_flag: false` by normalizing explanation warning flags before FastAPI response validation.
