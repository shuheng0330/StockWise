# StockWise

## Run Backend
python -m uvicorn stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000
python -m uvicorn --factory --app-dir src stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000

## Run Frontend

cd frontend
npm run dev
npm run dev -- -p 3001