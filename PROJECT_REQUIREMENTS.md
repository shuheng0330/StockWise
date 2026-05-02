# Project Requirements

Canonical requirements are maintained in `docs/project-requirements.md`.

Current history requirement:
- CSV uploads and manual entries are inventory observations.
- New uploads for any date range must append to the user's historical source observations and be sorted by actual uploaded `Date`.
- Dashboard and Records current tables show one latest snapshot per item.
- Records must retain the uncollapsed `source_observations[]` history used for trend-aware scoring.
- Re-uploading the same CSV must not duplicate identical source rows in calculation or Records history.
- If Supabase returns only partial history, the API must keep the previous latest analysis observations and append the new rows instead of replacing history with only the newest file.
- Raw historical rows are preferred for calculation; previous calculated item snapshots are fallback only when raw rows cannot be recovered.
- Upload/manual requests should send `base_analysis_id` so new rows append to the intended previous analysis.
- Analysis snapshots must persist their exact source observation stream so future uploads can reliably append to that history after backend restarts.
- Analysis snapshot persistence must not be skipped just because the longer `inventory_records` import persistence exceeded the response timeout.
- The analysis snapshot write is a required persistence step; it must not use the short optional Supabase operation timeout that protects long inventory-record imports.
