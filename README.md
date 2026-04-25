# StockWise

## Run Backend
$env:PYTHONPATH='src'; python -m stockwise_api.server
python -m uvicorn stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000
python -m uvicorn --factory --app-dir src stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000

On Windows, prefer `$env:PYTHONPATH='src'; python -m stockwise_api.server`. It sets the selector event-loop policy before Uvicorn starts, which avoids noisy Proactor socket reset traces when a browser or dev client closes a connection.

## Run Frontend

cd frontend
npm run dev
npm run dev -- -p 3001

## Deploy

Deploy the backend to Render with `render.yaml`, and deploy the frontend to Vercel with `frontend` as the project root. See `docs/deployment.md` for the required commands and environment variables.
