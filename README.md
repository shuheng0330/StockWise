# StockWise 📦
**Your AI-Powered Decision Partner for Inventory** [1]

## 📖 Description
StockWise is an inventory management solution built specifically for "Small Heroes," such as small cafe owners, kiosk operators, and kitchen leads [2]. It aims to eliminate the struggle of slow, messy, and scary spreadsheets by helping businesses move from manual data checking to confident decision-making [3]. By identifying high-value and high-waste items, StockWise reduces avoidable losses, frees up locked working capital, and helps users spot priorities in under two minutes [4, 5]. 

*Note: StockWise focuses on empathetic AI and decision support [6]. Features like automated ordering, IoT integrations, and profit forecasting are strictly out of scope [7].*

## ✨ Features
*   **Decision Dashboard:** Provides a fast operational overview and a snapshot of your stock health, easily highlighting high-value and high-waste items [4].
*   **Priority Action Board:** Uses trustworthy deterministic logic to rank urgency and waste-risk scores [8]. It offers clear labels and actions such as `RESTOCK_NOW`, `MONITOR_CLOSELY`, "Buy Less", or "Delay" [2, 8].
*   **What-If Simulator:** Allows you to test your ideas before spending cash [8]. You can simulate coverage and cash outlay for hypothetical scenarios (e.g., ordering 50 units) to avoid aggressive ordering mistakes [8].
*   **GLM Explanation Layer:** Powered by Z.AI GLM, this feature acts as an AI that "Speaks Human" [9]. It explains complex metrics and "The Why" behind decisions in plain language, stripping away analytical jargon for non-technical users [9].
*   **Interactive AI Partner:** An interactive chat interface with item cards where you can ask specific questions about your inventory analysis, such as "Why does this category look risky?" [5, 9].
*   **Reliability & Fallbacks:** Designed with a "Safety First" approach, it includes a 3-level fallback behavior so the system continues to work securely with deterministic rules even if the AI goes offline [7].

## 🚀 Ways to Use
You can easily integrate StockWise into your daily operational workflow (as showcased in your Live Demo):

1.  **Daily Overview:** Start your shift by checking the **Decision Dashboard** to view your overall stock health and identify any immediate waste risks [4].
2.  **Actioning Inventory:** Navigate to the **Priority Action Board** to see your ranked tasks. Follow the simple recommendations to restock, delay, or closely monitor specific items to reduce waste and save cash [2, 8].
3.  **Testing Order Scenarios:** Before placing a large vendor order, use the **What-If Simulator** to input your desired quantities and visualize the immediate impact on your cash outlay and stock coverage [8].
4.  **Chatting with your AI Partner:** If an item is flagged with a high risk score, open the **Interactive AI Partner** to ask for a plain-language explanation of the risk so you fully understand the data before deciding [5, 9]. 

## Run Backend
python -m uvicorn stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000
python -m uvicorn --factory --app-dir src stockwise_api.api.app:create_app --host 0.0.0.0 --port 8000

## Run Frontend

cd frontend
npm run dev
npm run dev -- -p 3001
