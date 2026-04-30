# Supabase Analysis Snapshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Supabase `analysis_runs.analysis_id` the main API `analysis_id` and persist analysis snapshots so analyses can be read after backend restart.

**Architecture:** Keep `inventory_records` as the source-of-truth observation table and add `analysis_runs` plus `analysis_item_results` as reproducible recommendation snapshots. API creation endpoints persist raw observations first, compute ranked analysis, persist the analysis snapshot, then return the Supabase-backed `analysis_id`.

**Tech Stack:** FastAPI, Pydantic, Supabase PostgREST client, pytest, Next.js frontend API client.

---

### Task 1: Add Supabase Migration For Analysis Snapshots

**Files:**
- Create: `supabase/migrations/202604220001_create_analysis_snapshots.sql`
- Modify: `docs/architecture-and-coding-design.md`
- Modify: `docs/project-requirements.md`

- [ ] **Step 1: Create the migration file**

Create `supabase/migrations/202604220001_create_analysis_snapshots.sql` with:

```sql
create table if not exists public.analysis_runs (
  analysis_id uuid not null default gen_random_uuid(),
  import_batch_id uuid null,
  source_type text not null check (source_type = any (array['manual'::text, 'import'::text])),
  date_range_start date null,
  date_range_end date null,
  observation_count integer not null check (observation_count >= 0),
  item_count integer not null check (item_count >= 0),
  formula_version text not null default 'stockwise-v1',
  created_by uuid null,
  created_at timestamp with time zone not null default now(),
  constraint analysis_runs_pkey primary key (analysis_id),
  constraint analysis_runs_import_batch_id_fkey foreign key (import_batch_id) references public.import_batches(import_batch_id),
  constraint analysis_runs_created_by_fkey foreign key (created_by) references public.profiles(id)
);

create table if not exists public.analysis_item_results (
  result_id uuid not null default gen_random_uuid(),
  analysis_id uuid not null,
  item_id uuid null,
  latest_record_id uuid null,
  rank_position integer not null check (rank_position >= 1),
  item_name text not null,
  category text null,
  subcategory text null,
  unit text not null,
  supplier_name text null,
  current_stock numeric not null,
  reorder_level numeric not null,
  daily_usage numeric not null,
  lead_time integer not null,
  price_per_unit numeric not null,
  seasonal_factor numeric not null,
  waste_percentage numeric not null,
  avg_usage_7d numeric not null,
  trend_direction text not null check (trend_direction = any (array['up'::text, 'down'::text, 'stable'::text])),
  days_of_cover numeric not null,
  inventory_value numeric not null,
  estimated_waste_cost numeric not null,
  lead_time_demand numeric not null,
  stock_gap_to_lead_demand numeric not null,
  reorder_urgency_score integer not null,
  waste_risk_score integer not null,
  recommended_action text not null check (recommended_action = any (array['RESTOCK_NOW'::text, 'BUY_LESS'::text, 'DELAY_PURCHASE'::text, 'MONITOR_CLOSELY'::text])),
  created_at timestamp with time zone not null default now(),
  constraint analysis_item_results_pkey primary key (result_id),
  constraint analysis_item_results_analysis_id_fkey foreign key (analysis_id) references public.analysis_runs(analysis_id) on delete cascade,
  constraint analysis_item_results_item_id_fkey foreign key (item_id) references public.items(item_id),
  constraint analysis_item_results_latest_record_id_fkey foreign key (latest_record_id) references public.inventory_records(record_id)
);

create index if not exists analysis_item_results_analysis_rank_idx
  on public.analysis_item_results (analysis_id, rank_position);

create index if not exists analysis_runs_created_at_idx
  on public.analysis_runs (created_at desc);
```

- [ ] **Step 2: Do not push the migration automatically**

Tell the user to run this only after review:

```powershell
supabase link --project-ref fujcmskmahkvyulzxvuy
supabase db push
```

Expected: Supabase applies the migration and shows it in Database Migrations.

---

### Task 2: Persist Analysis Runs And Results

**Files:**
- Modify: `src/stockwise_api/store.py`
- Test: `tests/services/test_supabase_store.py`

- [ ] **Step 1: Write failing store tests**

Add tests proving `SupabaseAnalysisStore.create_analysis_snapshot(...)` inserts one `analysis_runs` row and one `analysis_item_results` row per ranked item, returning the Supabase `analysis_id`.

- [ ] **Step 2: Implement `create_analysis_snapshot`**

Add a method with this signature:

```python
def create_analysis_snapshot(
    self,
    *,
    dataset_summary: dict,
    ranked_items: list[dict],
    source_type: str,
    import_batch_id: str | None = None,
    created_by: str | None = None,
    formula_version: str = "stockwise-v1",
) -> str:
```

It should insert into `analysis_runs`, then insert into `analysis_item_results` with `rank_position`.

- [ ] **Step 3: Implement `get` for Supabase snapshots**

`SupabaseAnalysisStore.get(analysis_id)` should query `analysis_runs` and `analysis_item_results`, rebuild `dataset_summary`, compute `kpi_summary` from rows, and return `AnalysisRecord`.

---

### Task 3: Make Supabase `analysis_id` The API ID

**Files:**
- Modify: `src/stockwise_api/api/app.py`
- Test: `tests/api/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests with a fake Supabase store proving create endpoints return the `analysis_id` from `create_analysis_snapshot`.

- [ ] **Step 2: Update `_save_analysis`**

When a Supabase store exists, call `create_analysis_snapshot` after ranking and use that returned ID for the in-memory cache. When no Supabase store exists, keep using `InMemoryAnalysisStore.create`.

- [ ] **Step 3: Make `GET /api/v1/analyses/{analysis_id}` resilient**

Try in-memory first. If missing, try `supabase_store.get(analysis_id)`. If Supabase is disabled or missing the record, return 404.

---

### Task 4: Keep Observation Persistence Linked To Analysis

**Files:**
- Modify: `src/stockwise_api/store.py`
- Modify: `src/stockwise_api/api/app.py`
- Test: `tests/services/test_supabase_store.py`
- Test: `tests/api/test_api.py`

- [ ] **Step 1: Return `import_batch_id` from observation persistence**

`persist_observations` already returns `import_batch_id`, `successful_rows`, and `failed_rows`. API upload should keep that value and pass it into `create_analysis_snapshot`.

- [ ] **Step 2: Preserve source type**

CSV upload snapshots use `source_type = import`. Manual snapshots use `source_type = manual`.

---

### Task 5: Documentation And Verification

**Files:**
- Modify: `docs/project-requirements.md`
- Modify: `docs/architecture-and-coding-design.md`
- Modify: `docs/project-status.md`

- [ ] **Step 1: Update docs**

Document:

```text
analysis_runs.analysis_id is the API analysis_id when Supabase persistence is enabled.
inventory_records store source observations.
analysis_item_results store point-in-time recommendations.
```

- [ ] **Step 2: Run backend tests**

Run:

```powershell
python -m pytest
```

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
npm.cmd run build
```

Expected: Next.js production build completes.

- [ ] **Step 4: Run real dataset smoke test**

Run a local TestClient upload of `restaurant_inventory_100days.csv`.

Expected:

```text
row_count 1000
item_count 10
items_len 10
unique_item_ids 10
```

---

## Self-Review

- Spec coverage: The plan covers migration creation, snapshot persistence, API ID ownership, read-after-restart, docs, and verification.
- Placeholder scan: No placeholder-only implementation steps remain; each task names concrete files and expected behavior.
- Type consistency: The plan consistently uses `analysis_id`, `analysis_runs`, `analysis_item_results`, `source_type`, `import_batch_id`, and `formula_version`.
