# StockWise Deployment

This repo deploys as two services:

- Backend API: Render web service from the repository root.
- Frontend app: Vercel project with `frontend` as the root directory.

## Render Backend

Use the included `render.yaml` as a Render Blueprint, or create a Python web service manually with:

- Build command: `pip install -r requirements.txt`
- Start command: `PYTHONPATH=src python -m uvicorn --factory stockwise_api.api.app:create_app --host 0.0.0.0 --port $PORT`

Set these Render environment variables:

```env
STOCKWISE_CORS_ORIGINS=https://your-vercel-project.vercel.app
STOCKWISE_SUPABASE_ENABLED=true
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
GLM_MODE=mock
ZAI_API_KEY=
```

Use `GLM_MODE=live` only when `ZAI_API_KEY` is set.

## Vercel Frontend

Import the same Git repository into Vercel and set:

- Root Directory: `frontend`
- Framework Preset: Next.js
- Install Command: `npm ci`
- Build Command: `npm run build`

Set these Vercel environment variables:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-service.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

After Vercel gives you the production URL, add that exact URL to `STOCKWISE_CORS_ORIGINS` on Render and redeploy the backend.
