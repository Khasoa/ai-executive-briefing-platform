# n8n → Briefly daily / weekly orchestration

n8n is an **orchestration layer only**. All sync and AI logic stays in FastAPI.

## Security

Set on the Briefly API:

```bash
N8N_WEBHOOK_SECRET=a-long-random-secret
```

Every n8n HTTP Request node must send:

```http
X-Briefly-N8N-Secret: <same secret>
Content-Type: application/json
```

If the secret is unset, endpoints return `503`. Wrong secret → `401`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/webhooks/n8n/daily` | Sync providers + regenerate Morning Brief |
| `POST` | `/webhooks/n8n/weekly` | Sync providers + regenerate Weekly Digest |
| `POST` | `/webhooks/n8n/run` | Custom mix of sync / regenerate flags |

### Body (optional)

```json
{
  "userEmail": "lydia@arcadiasystems.com",
  "userId": null,
  "providers": ["google-calendar", "gmail", "notion", "gohighlevel", "monday", "clickup"],
  "regenerateMorningBrief": true,
  "regenerateWeeklyDigest": false
}
```

If `userEmail` / `userId` are omitted, Briefly uses the demo executive user.

## Recommended daily workflow

1. **Schedule** — cron before the executive’s delivery time (e.g. `25 6 * * 1-5`).
2. **HTTP Request** → `POST {{BRIEFY_API}}/webhooks/n8n/daily` with secret header.
3. **Optional IF** — branch on `body.partial === true` to notify Slack/email that some providers failed.
4. Do **not** re-implement sync or brief assembly in n8n Function nodes.

## Recommended weekly workflow

1. **Schedule** — e.g. Sunday evening or Monday 05:00.
2. **HTTP Request** → `POST {{BRIEFY_API}}/webhooks/n8n/weekly`.

## Failure isolation

Each provider sync is a separate step. Example response:

```json
{
  "ok": false,
  "partial": true,
  "steps": [
    { "provider": "google-calendar", "status": "success" },
    { "provider": "gmail", "status": "error", "detail": "…" },
    { "provider": "notion", "status": "skipped", "detail": "Notion is not connected" },
    { "provider": "gohighlevel", "status": "success" },
    { "provider": "morning-brief", "status": "success" }
  ]
}
```

- `skipped` — not connected / missing scope (continue).
- `error` — provider failed (continue other steps).
- Morning Brief / Weekly Digest still run unless those steps themselves error.

## Production checklist

1. HTTPS API URL reachable from n8n.
2. Strong `N8N_WEBHOOK_SECRET` (rotate periodically).
3. Prefer `userEmail` of a real user when `AUTH_REQUIRED=true`.
4. Connect Google / Notion / GHL for that user in the Briefly UI first.
5. Keep n8n workflows free of CRM/email/calendar parsing.
