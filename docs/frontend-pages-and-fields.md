# StockWise Frontend Pages and Field Requirements

## Purpose
This document lists the MVP frontend pages, the features on each page, and the fields/items needed from the backend contract.

The backend source of truth for request and response shapes is:
- `src/stockwise_api/schemas.py`
- `src/stockwise_api/contracts.py`
- `docs/project-requirements.md`

## Page 1: Entry Page

## Purpose
Let a cafe owner start an analysis either by uploading a CSV or manually entering items.

## Backend Endpoints
- CSV upload: `POST /api/v1/analyses`
- Manual entry: `POST /api/v1/manual-analyses`

## Main Features
- Choose input mode: `Upload CSV` or `Manual Entry`
- Upload CSV file
- Show accepted CSV headers and downloadable/example template
- Add, duplicate, and remove manual item rows
- Validate required fields before submit
- Explain that score-driving fields affect recommendations
- Submit inventory and navigate to the analysis dashboard
- Show backend validation errors clearly

## Manual Entry Required Fields
- `item_name`
- `current_stock`
- `unit`
- `usage_value`
- `usage_period`
- `lead_time_days`
- `price_per_unit`
- `seasonal_factor`
- waste signal: either `perishability_level` or `recent_waste_percentage`

## Manual Entry Optional Fields
- `category`
- `subcategory`
- `supplier_name`
- `manual_reorder_level`

## Recommended Field Controls
- `item_name`: text input
- `current_stock`: number input, minimum `0`
- `unit`: dropdown or combobox, examples `kg`, `litre`, `pieces`, `pack`, `box`
- `usage_value`: number input, greater than `0`
- `usage_period`: dropdown with `daily`, `weekly`
- `lead_time_days`: number input, integer greater than `0`
- `price_per_unit`: number input, minimum `0`, helper text: "Estimate is okay"
- `seasonal_factor`: guided dropdown
- `perishability_level`: guided dropdown
- `recent_waste_percentage`: advanced number input, minimum `0`
- `manual_reorder_level`: advanced number input, minimum `0`
- `category`: text input or dropdown
- `subcategory`: text input or dropdown
- `supplier_name`: text input

## Suggested Dropdown Values
- `usage_period`
- `daily`
- `weekly`

- `seasonal_factor`
- `Low demand`: `0.8`
- `Normal`: `1.0`
- `Busy`: `1.2`
- `Peak`: `1.4`

- `perishability_level`
- `Low`: dry goods, canned goods, long shelf life
- `Medium`: chilled or moderately perishable goods
- `High`: fresh dairy, produce, prepared ingredients

## CSV Upload Requirements
- Owner-friendly CSV headers may use the same field names as manual entry.
- Legacy CSV headers are also accepted by the backend.
- Legacy `Daily_Usage` maps to `usage_value` with `usage_period = daily`.
- Legacy `Waste_Percentage` maps to `recent_waste_percentage` and satisfies the waste-signal requirement.

## CSV Template Headers
Use this owner-friendly CSV header order for frontend examples:

```csv
item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,seasonal_factor,perishability_level,category,subcategory,supplier_name,manual_reorder_level,recent_waste_percentage
```

## Page 2: Analysis Dashboard

## Purpose
Show the ranked recommendation output after CSV upload or manual entry.

## Backend Source
- Response from `POST /api/v1/analyses`
- Response from `POST /api/v1/manual-analyses`

## Main Features
- KPI summary cards
- Ranked item recommendation table
- Action filters: `RESTOCK_NOW`, `BUY_LESS`, `DELAY_PURCHASE`, `MONITOR_CLOSELY`
- Search by item name, category, supplier, or action
- Highlight high urgency and high waste-risk items
- Navigate to records review/edit page
- Open simulation modal/page for an item
- Open explanation drawer/modal for an item

## KPI Fields
- `item_count`
- `restock_now_count`
- `buy_less_count`
- `high_waste_risk_count`
- `inventory_value_at_risk`
- `top_urgent_items`
- `top_waste_cost_items`

## Ranked Item Fields
- `item_id`
- `item_name`
- `category`
- `subcategory`
- `unit`
- `supplier_name`
- `current_stock`
- `reorder_level`
- `daily_usage`
- `lead_time`
- `price_per_unit`
- `seasonal_factor`
- `waste_percentage`
- `days_of_cover`
- `inventory_value`
- `estimated_waste_cost`
- `lead_time_demand`
- `stock_gap_to_lead_demand`
- `reorder_urgency_score`
- `waste_risk_score`
- `recommended_action`

## Recommended Display Priority
- Always show: `item_name`, `recommended_action`, `current_stock`, `daily_usage`, `days_of_cover`, `reorder_urgency_score`, `waste_risk_score`
- Show in expanded/details view: `price_per_unit`, `seasonal_factor`, `waste_percentage`, `inventory_value`, `estimated_waste_cost`, `lead_time_demand`, `stock_gap_to_lead_demand`

## Page 3: Records Review and Edit Page

## Purpose
Let the owner review, edit, or delete uploaded/manual records before relying on the dashboard.

## Backend Endpoints
- Get records: `GET /api/v1/analyses/{analysis_id}/records`
- Update record: `PATCH /api/v1/analyses/{analysis_id}/items/{item_id}`
- Delete record: `DELETE /api/v1/analyses/{analysis_id}/items/{item_id}`

## Main Features
- Editable inventory records table
- Inline edit or edit drawer
- Delete item with confirmation
- Recompute recommendation after edits
- Show current `recommended_action` after update
- Prevent deleting the final remaining item

## Editable Fields
- `item_name`
- `current_stock`
- `unit`
- `usage_value`
- `usage_period`
- `lead_time_days`
- `price_per_unit`
- `seasonal_factor`
- `category`
- `subcategory`
- `supplier_name`
- `perishability_level`
- `manual_reorder_level`
- `recent_waste_percentage`

## Read-Only or System Fields
- `item_id`
- `last_updated`
- `daily_usage`
- `recommended_action`

## Edit Validation Rules
- `current_stock` must be `>= 0`
- `usage_value` must be `> 0`
- `lead_time_days` must be `> 0`
- `price_per_unit` must be `>= 0`
- `seasonal_factor` must be `>= 0`
- `manual_reorder_level` must be `>= 0`
- `recent_waste_percentage` must be `>= 0`
- At least one waste signal should remain available after edit: `perishability_level` or `recent_waste_percentage`

## Page 4: Item Simulation Page or Modal

## Purpose
Let the owner test a reorder quantity before deciding what to buy.

## Backend Endpoint
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/simulate`

## Main Features
- Choose one ranked item
- Enter proposed reorder quantity
- Show simulated cost, coverage, inventory value, waste cost, risk change, and updated recommendation
- Allow user to compare current recommendation versus simulated result

## Input Fields
- `simulated_order_qty`

## Simulation Output Fields
- `item_id`
- `simulated_order_qty`
- `simulated_cash_outlay`
- `simulated_coverage_days`
- `simulated_inventory_value`
- `simulated_estimated_waste_cost`
- `simulated_risk_change`
- `reorder_urgency_score`
- `waste_risk_score`
- `recommended_action`

## Page 5: Explanation Drawer or Page

## Purpose
Explain why the system recommended a specific action.

## Backend Endpoint
- `POST /api/v1/analyses/{analysis_id}/items/{item_id}/explanation`

## Main Features
- Show explanation for an item recommendation
- Optionally include the latest simulation context
- Show whether the explanation came from `mock`, `live`, or `fallback`
- Keep deterministic recommendation visible even if model explanation falls back

## Optional Request Fields
- `simulated_order_qty`
- `simulated_cash_outlay`
- `simulated_coverage_days`
- `simulated_risk_change`

## Explanation Output Fields
- `source`
- `item_name`
- `recommended_action`
- `priority_level`
- `short_reason`
- `decision_explanation`
- `tradeoff_summary`
- `suggested_next_step`
- `confidence_note`
- `warning_flag`

## Page 6: Error and Empty States

## Purpose
Make validation and API failures understandable for non-technical users.

## Main States
- Empty CSV upload
- Invalid CSV headers
- Missing required score-driving fields
- Invalid numeric values
- Invalid dropdown values
- Unknown `analysis_id`
- Unknown `item_id`
- Cannot delete the final remaining item
- Explanation fallback used
- Loading state for analysis, simulation, record update, and explanation

## Error Display Items
- Human-friendly title
- Specific field or row if available
- Backend `error_code`
- Backend `message`
- Recommended next action

## Shared UI Components

## Inventory Item Form
Used by:
- Manual entry page
- Record edit drawer/modal

Fields:
- Required identity and stock fields
- Required score-driving fields
- Optional organization fields
- Advanced override fields

## Recommendation Badge
Used by:
- Dashboard
- Records page
- Simulation result
- Explanation drawer

Values:
- `RESTOCK_NOW`
- `BUY_LESS`
- `DELAY_PURCHASE`
- `MONITOR_CLOSELY`

## Score Badge
Used by:
- Dashboard
- Simulation result

Fields:
- `reorder_urgency_score`
- `waste_risk_score`

## Advanced Fields Section
Used by:
- Manual entry page
- Record edit drawer/modal

Fields:
- `manual_reorder_level`
- `recent_waste_percentage`

Copy:
- "Use these only if you know the exact value. Otherwise, the guided choices above are enough."

## MVP Navigation
- Entry Page
- Analysis Dashboard
- Records Review/Edit
- Simulation Modal or Item Detail
- Explanation Drawer

Authentication, account settings, persistent history, and role management are outside the current MVP scope.
