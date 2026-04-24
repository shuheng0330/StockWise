alter table public.items
  add column if not exists owner_id uuid null references public.profiles(id);

alter table public.suppliers
  add column if not exists owner_id uuid null references public.profiles(id);

update public.inventory_records as records
set created_by = batches.uploaded_by
from public.import_batches as batches
where records.created_by is null
  and records.import_batch_id = batches.import_batch_id
  and batches.uploaded_by is not null;

update public.analysis_runs as runs
set created_by = batches.uploaded_by
from public.import_batches as batches
where runs.created_by is null
  and runs.import_batch_id = batches.import_batch_id
  and batches.uploaded_by is not null;

update public.items as items
set owner_id = item_owners.owner_id
from (
  select item_id, min(created_by::text)::uuid as owner_id
  from public.inventory_records
  where created_by is not null
  group by item_id
) as item_owners
where items.item_id = item_owners.item_id
  and items.owner_id is null;

update public.suppliers as suppliers
set owner_id = supplier_owners.owner_id
from (
  select supplier_id, min(owner_id::text)::uuid as owner_id
  from public.items
  where supplier_id is not null
    and owner_id is not null
  group by supplier_id
) as supplier_owners
where suppliers.supplier_id = supplier_owners.supplier_id
  and suppliers.owner_id is null;

create index if not exists inventory_records_created_by_record_date_idx
  on public.inventory_records (created_by, record_date desc, created_at desc);

create index if not exists analysis_runs_created_by_created_at_idx
  on public.analysis_runs (created_by, created_at desc);

create index if not exists items_owner_identity_idx
  on public.items (owner_id, item_name, unit, category, subcategory);

create index if not exists suppliers_owner_name_idx
  on public.suppliers (owner_id, supplier_name);

do $$
begin
  if exists (select 1 from public.items where owner_id is null) then
    raise notice 'items.owner_id still has null rows after backfill; local/dev data reset may be required before setting NOT NULL.';
  else
    alter table public.items alter column owner_id set not null;
  end if;

  if exists (select 1 from public.suppliers where owner_id is null) then
    raise notice 'suppliers.owner_id still has null rows after backfill; local/dev data reset may be required before setting NOT NULL.';
  else
    alter table public.suppliers alter column owner_id set not null;
  end if;
end
$$;
