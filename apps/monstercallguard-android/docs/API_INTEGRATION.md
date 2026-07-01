# Monster Call Guard — API Integration

**Base URL:** `https://<your-tunnel>.trycloudflare.com` (Cloudflare Tunnel HTTPS only)

Developed by Suckbob | Monster AI Call Guard

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/api/callguard/status` | Engine status |
| GET | `/api/callguard/connection` | Tunnel URL hint |
| POST | `/api/callguard/analyze` | Call scoring + `trust_score` |
| POST | `/api/callguard/report` | Anonymous hash report |
| GET | `/api/callguard/consensus` | Vote queue (no public board) |
| GET | `/api/callguard/threat-db` | Local rules sync |
| POST | `/api/callguard/token` | Short-lived client token |

## Analyze response

```json
{
  "score": 72,
  "trust_score": 28,
  "reject": false,
  "blocked": true,
  "category": "debt_collection",
  "signals": ["prefix:+8529", "display:收數"],
  "public_board": false
}
```

## Android client stack

- **OkHttp** + `RetryInterceptor` (3 retries)
- **Retrofit** `MonsterApiService`
- **WorkManager** — threat-db sync (6h), health probe (30min)
- **Offline cache** — `files/threat_db.json`, `last_health.json`

## Dify / Make / Sentry

- Dify: `deploy/dify/workflow_callguard_trust.json`
- Make: `deploy/make/SCENARIO.md`
- Sentry: `client/src/lib/sentry.ts` + backend `integrations.sentry_dsn`