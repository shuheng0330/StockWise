create table if not exists public.analysis_source_observations (
  analysis_id uuid not null,
  row_number integer not null check (row_number >= 1),
  observation_data jsonb not null,
  created_at timestamp with time zone not null default now(),
  constraint analysis_source_observations_pkey primary key (analysis_id, row_number),
  constraint analysis_source_observations_analysis_id_fkey foreign key (analysis_id) references public.analysis_runs(analysis_id) on delete cascade
);

create index if not exists analysis_source_observations_analysis_row_idx
  on public.analysis_source_observations (analysis_id, row_number);
