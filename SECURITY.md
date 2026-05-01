# Security Policy

## Supported Versions

This project is an active hackathon submission. Only the `main` branch is supported.

## Reporting a Vulnerability

If you discover a security vulnerability in StockWise, please **do not open a public issue**. Instead, email the maintainer:

- **Lim Wey Cheng** — weychenglim@gmail.com

Include:
- A description of the vulnerability and its impact
- Steps to reproduce (proof of concept if possible)
- Any suggested mitigation

You can expect an acknowledgement within 72 hours and a remediation plan within 7 days for confirmed issues.

## Credential & Secret Handling

- The Supabase **service role key** is server-side only. It is loaded by the FastAPI backend from `.env` (gitignored) and never exposed to the browser.
- The frontend only ever receives the Supabase **anon key** via `NEXT_PUBLIC_*` variables, which are subject to Row-Level Security policies defined in [supabase/migrations/](supabase/migrations/).
- Production secrets (Supabase keys, Z.AI API key) are injected at runtime via Render environment variables (`sync: false` in [render.yaml](render.yaml)) and Vercel project settings — they are never committed.
- If a secret is suspected to have leaked, rotate it immediately:
  - Supabase: Dashboard → Settings → API → Reset keys
  - Z.AI: Revoke and reissue from the Z.AI console
  - Gemini: Revoke and reissue from Google AI Studio

## CORS & Environment Configuration

The FastAPI backend is configured with an explicit CORS allowlist — wildcard origins are never used.

- **Allowed origins** are built in [src/stockwise_api/api/app.py:381](src/stockwise_api/api/app.py#L381) (`_cors_origins_from_env`). The list combines:
  - Hardcoded local-dev origins (`http://localhost:3000-3002` and `127.0.0.1` equivalents)
  - Production origins read from the `STOCKWISE_CORS_ORIGINS` env var (comma-separated)
- The deployed Vercel frontend URL is added to `STOCKWISE_CORS_ORIGINS` on Render via `sync: false` in [render.yaml](render.yaml#L11) — never committed to source.
- The `CORSMiddleware` at [app.py:595](src/stockwise_api/api/app.py#L595) restricts `allow_origins` to this list, blocking unauthorized cross-origin requests.

### Required environment variables

| Scope | Variable | Sensitivity |
|---|---|---|
| Backend (server-only) | `SUPABASE_SERVICE_ROLE_KEY` | **High** — bypasses RLS |
| Backend (server-only) | `ZAI_API_KEY` | **High** — paid API access |
| Backend (config) | `STOCKWISE_CORS_ORIGINS` | Low — public origin list |
| Backend (config) | `GLM_MODE` | Low — `mock` or `live` |
| Frontend (public) | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Low — RLS-gated |
| Frontend (public) | `NEXT_PUBLIC_API_BASE_URL` | Low — public backend URL |

All `NEXT_PUBLIC_*` variables ship to the browser bundle by design (Next.js convention). The service role key and Z.AI key **must never** carry the `NEXT_PUBLIC_` prefix.

## Supabase Row-Level Security & User Ownership

User data is partitioned by Supabase Auth user ID. RLS policies are enforced at the database layer — even if a request bypasses application-level checks, Postgres rejects unauthorized reads/writes.

- **Migration 1** — [supabase/migrations/202604220001_create_analysis_snapshots.sql](supabase/migrations/202604220001_create_analysis_snapshots.sql): creates the analysis snapshot tables and enables RLS.
- **Migration 2** — [supabase/migrations/202604240001_add_user_ownership_to_items_and_suppliers.sql](supabase/migrations/202604240001_add_user_ownership_to_items_and_suppliers.sql): adds `owner_user_id` columns to items and suppliers, with policies restricting `SELECT`/`INSERT`/`UPDATE`/`DELETE` to rows where `owner_user_id = auth.uid()`.

**Trust boundary:**
1. Browser holds the Supabase **anon key** + a JWT issued by Supabase Auth on login.
2. Frontend sends the JWT to the FastAPI backend.
3. Backend validates the JWT and uses the **service role key** to query Supabase. RLS policies still apply in queries that filter by `owner_user_id`.
4. The service role key never crosses the network back to the browser.

This means a user cannot read or modify another user's inventory data even if they tamper with the frontend or call the API directly with their own JWT.

## Dependency Hygiene

- Dependabot runs weekly against `pip` and `npm` ecosystems (see [.github/dependabot.yml](.github/dependabot.yml)).
- All PRs run the CI pipeline (typecheck, unit tests, production build) before merge.

## Scope

In scope:
- Authentication / authorization bypass
- Injection (SQL, prompt injection of the AI Copilot)
- Secret exposure in client bundles or logs
- RLS policy gaps in Supabase migrations

Out of scope:
- Issues requiring physical access to a user's device
- Social engineering
- DoS via unauthenticated public endpoints (rate limiting is a known limitation)
