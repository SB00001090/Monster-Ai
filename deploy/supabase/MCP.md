# Supabase MCP + Agent Skills

Project ref: **`unoayywzgfkrtnjsrkdq`**  
MCP URL: `https://mcp.supabase.com/mcp?project_ref=unoayywzgfkrtnjsrkdq`

## Grok (this repo)

Already configured in [`.grok/config.toml`](../../.grok/config.toml).

1. In Grok TUI run **`/mcps`**
2. Select **supabase** → press **`i`** to authenticate (browser OAuth)
3. After login, ask: *"List tables in the database using MCP"*

Verify:

```bash
grok mcp doctor supabase
```

Expected before auth: `OAuth authorization required`  
Expected after auth: handshake OK + tools listed

## Cursor

Add to **Settings → Tools & MCP** or use project [`.mcp.json`](../../.mcp.json):

```json
{
  "mcpServers": {
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=unoayywzgfkrtnjsrkdq"
    }
  }
}
```

Restart Cursor after first OAuth login.

## GitHub Copilot

```bash
copilot mcp add --transport http supabase "https://mcp.supabase.com/mcp?project_ref=unoayywzgfkrtnjsrkdq"
copilot -i /mcp
```

Or `~/.copilot/mcp-config.json` with the same `url`.

## Agent Skills (optional)

```bash
npx skills add supabase/agent-skills -y
```

Installs `supabase` and `supabase-postgres-best-practices` skills for schema, RLS, and performance guidance.

## Useful MCP tools

| Tool | Use |
|------|-----|
| `list_tables` | Check if `guardian_profiles` exists |
| `apply_migration` | Deploy schema from repo |
| `execute_sql` | Run ad-hoc SQL |
| `get_publishable_keys` | Fetch anon key for `.env` |
| `generate_typescript_types` | Types for `client/src` |

## Security

- Scoped to project `unoayywzgfkrtnjsrkdq` only
- Prefer **read-only** for exploration: append `&read_only=true` to MCP URL
- Do not connect MCP to production user data