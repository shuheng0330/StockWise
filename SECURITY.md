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
