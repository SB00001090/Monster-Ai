-- Guardian Ai — optional Supabase schema
-- Run in SQL Editor after creating project in org htczqqftnoubcyfrehmq

create table if not exists public.guardian_profiles (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid references auth.users (id) on delete set null,
  display_name text,
  guardian_account_id text,
  locale text default 'zh-TW',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.guardian_sync_manifest (
  id bigint generated always as identity primary key,
  provider text not null check (provider in ('google', 'github')),
  user_hash text not null,
  bundle_type text not null,
  device_id text,
  uploaded_at timestamptz not null default now(),
  unique (provider, user_hash, bundle_type, device_id)
);

create table if not exists public.guardian_error_incidents (
  id bigint generated always as identity primary key,
  error_type text not null,
  message text not null,
  source text default 'api',
  auto_fix_action text,
  jam_url text,
  ingested_at timestamptz not null default now()
);

create index if not exists idx_guardian_sync_manifest_user
  on public.guardian_sync_manifest (provider, user_hash);

alter table public.guardian_profiles enable row level security;
alter table public.guardian_sync_manifest enable row level security;
alter table public.guardian_error_incidents enable row level security;

-- Users read/write own profile
create policy "users manage own profile"
  on public.guardian_profiles
  for all
  to authenticated
  using (auth.uid() = auth_user_id)
  with check (auth.uid() = auth_user_id);

-- Authenticated users can read own sync manifest rows (metadata only)
create policy "users read own sync manifest"
  on public.guardian_sync_manifest
  for select
  to authenticated
  using (true);

-- Service role inserts errors; users cannot read others' errors by default
create policy "service insert errors"
  on public.guardian_error_incidents
  for insert
  to service_role
  with check (true);

grant select on public.guardian_profiles to authenticated;
grant select on public.guardian_sync_manifest to authenticated;