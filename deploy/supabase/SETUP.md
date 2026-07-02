# Guardian Ai × Supabase

Developed by Suckbob | Guardian Ai

**Organization:** [htczqqftnoubcyfrehmq](https://supabase.com/dashboard/org/htczqqftnoubcyfrehmq)

Guardian Ai remains **local-first**. Supabase is optional cloud mirror for profiles, sync manifests, and error incident backup — not a replacement for E2E encrypted vaults.

## 1. Create project (Dashboard)

1. Open your [Supabase organization](https://supabase.com/dashboard/org/htczqqftnoubcyfrehmq).
2. **New project** → name e.g. `guardian-ai` → region **`ap-southeast-2`** (Sydney).
3. Save the database password securely.

## 2. Connect GitHub (recommended)

See **[GITHUB.md](GITHUB.md)** for full steps.

Quick summary:

1. **Project Settings → Integrations → GitHub** → Authorize
2. Repository: `SB00001090/Guardian-Ai`
3. **Working directory:** `deploy`
4. Enable **Deploy to production**

Migrations live in `deploy/supabase/migrations/` and deploy on push to `main`.

## 3. Run schema (manual alternative)

If you are **not** using GitHub Integration yet, run [`guardian_schema.sql`](guardian_schema.sql) in **SQL Editor**.

## 4. Enable Auth providers (optional)

**Authentication → Providers:** enable Google, GitHub, Discord to mirror Guardian OAuth.

Redirect URL (local dev):

```
http://localhost:3000/api/oauth/callback
http://127.0.0.1:7860/login
```

Production: add your Cloudflare Pages URL.

## 5. Environment variables

Copy from **Project Settings → API**:

```env
VITE_SUPABASE_URL=https://xxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Server-only (optional — error/sync backup jobs)
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Add to `.env` and Cloudflare Pages env.

## 6. MCP + Agent Skills (optional)

See **[MCP.md](MCP.md)** — Grok `/mcps` OAuth, Cursor `.mcp.json`, Copilot `mcp-config.json`, and `npx skills add supabase/agent-skills`.

## 7. Verify

1. Restart `run.bat` or `pnpm dev` + `python main.py`.
2. Open `/integrations` → **Supabase** row should show green when URL + anon key are set.
3. `GET /api/integrations/status` includes `supabase_configured: true`.

## Notes

- Node tRPC still uses MySQL or `.monster-data/` JSON when `DATABASE_URL` is unset.
- Supabase Postgres schema is **separate** from Drizzle MySQL tables — no auto-migration yet.
- Guardian E2E sync bundles stay encrypted; only metadata (provider, user_hash, bundle_type) may mirror to Supabase if you enable server backup later.