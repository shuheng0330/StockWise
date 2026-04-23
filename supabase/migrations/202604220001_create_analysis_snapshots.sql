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
  app_item_id integer not null,
  latest_record_date date not null,
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
