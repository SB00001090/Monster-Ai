# Guardian Ai × Supabase

Developed by Suckbob | Guardian Ai

**Organization:** [htczqqftnoubcyfrehmq](https://supabase.com/dashboard/org/htczqqftnoubcyfrehmq)

Guardian Ai remains **local-first**. Supabase is optional cloud mirror for profiles, sync manifests, and error incident backup — not a replacement for E2E encrypted vaults.

## 1. Create project (Dashboard)

1. Open your [Supabase organization](https://supabase.com/dashboard/org/htczqqftnoubcyfrehmq).
2. **New project** → name e.g. `guardian-ai` → region **`ap-southeast-2`** (Sydney).
3. Save the database password securely.

## 2. Run schema

In **SQL Editor**, paste and run [`guardian_schema.sql`](guardian_schema.sql).

## 3. Enable Auth providers (optional)

**Authentication → Providers:** enable Google, GitHub, Discord to mirror Guardian OAuth.

Redirect URL (local dev):

```
http://localhost:3000/api/oauth/callback
http://127.0.0.1:7860/login
```

Production: add your Cloudflare Pages URL.

## 4. Environment variables

Copy from **Project Settings → API**:

```env
VITE_SUPABASE_URL=https://xxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Server-only (optional — error/sync backup jobs)
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Add to `.env` and Cloudflare Pages env.

## 5. Verify

1. Restart `run.bat` or `pnpm dev` + `python main.py`.
2. Open `/integrations` → **Supabase** row should show green when URL + anon key are set.
3. `GET /api/integrations/status` includes `supabase_configured: true`.

## Notes

- Node tRPC still uses MySQL or `.monster-data/` JSON when `DATABASE_URL` is unset.
- Supabase Postgres schema is **separate** from Drizzle MySQL tables — no auto-migration yet.
- Guardian E2E sync bundles stay encrypted; only metadata (provider, user_hash, bundle_type) may mirror to Supabase if you enable server backup later.