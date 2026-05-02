# Architecture and Coding Design

Canonical architecture notes are maintained in `docs/architecture-and-coding-design.md`.

Current upload-history design:
- `POST /api/v1/analyses` validates CSV rows, persists them as source observations, then builds a fresh analysis snapshot.
- `POST /api/v1/manual-analyses` follows the same observation-history path.
- Create flows build a baseline from previous raw source observations plus newly submitted rows, then use complete persisted history when available.
- Frontend Dashboard/Data Entry navigation carries the current analysis as `baseAnalysisId`; upload/manual submit sends it as `base_analysis_id` so backend history assembly starts from the intended prior analysis.
- Supabase `analysis_source_observations` stores the exact observation stream for each snapshot, making previous analysis history durable across process restarts and ownership-backfill gaps.
- Analysis snapshot writes are attempted even when long-running inventory observation persistence times out, so uploads can still produce durable `analysis_runs` and `analysis_source_observations` records.
- `create_analysis_snapshot` is intentionally called outside the optional Supabase timeout wrapper because `analysis_runs` is the durable API analysis identity; failures are logged with `stockwise.analysis_snapshot.*` events and the in-memory fallback is used only after an actual exception.
- `/health` exposes `snapshot_write_mode = required`, `history_snapshot_table`, and `supabase_store_ready` so deployments can be checked before upload testing.
- Supabase-loaded analyses keep `source_observations` when copied into the in-memory cache, preventing follow-up uploads from falling back to latest item snapshots.
- If previous raw rows are unavailable, create flows convert previous latest item snapshots into source-like fallback observations before appending new raw rows.
- Exact duplicate source observations are deduplicated, the merged stream is sorted by uploaded `Date`, and AI receives compact history summaries rather than raw CSV rows.
