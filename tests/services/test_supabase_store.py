from stockwise_api.store import SupabaseAnalysisStore


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    def __init__(self, database, table_name):
        self.database = database
        self.table_name = table_name
        self.operation = "select"
        self.payload = None
        self.filters = []
        self.order_by = None
        self.order_desc = False
        self.row_limit = None

    def select(self, *_columns):
        self.operation = "select"
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, column, desc=False):
        self.order_by = column
        self.order_desc = desc
        return self

    def limit(self, count):
        self.row_limit = count
        return self

    def execute(self):
        rows = self.database.setdefault(self.table_name, [])
        if self.operation == "insert":
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            id_columns = {
                "analysis_item_results": "result_id",
                "analysis_runs": "analysis_id",
                "import_batches": "import_batch_id",
                "import_row_errors": "error_id",
                "inventory_records": "record_id",
                "items": "item_id",
                "suppliers": "supplier_id",
            }
            id_column = id_columns.get(self.table_name)
            inserted = []
            for raw_payload in payloads:
                payload = dict(raw_payload)
                if id_column and id_column not in payload:
                    payload[id_column] = f"{self.table_name}-{len(rows) + 1}"
                rows.append(payload)
                inserted.append(payload)
            return FakeResult(inserted)

        if self.operation == "update":
            matched = [row for row in rows if self._matches(row)]
            for row in matched:
                row.update(self.payload)
            return FakeResult(matched)

        selected = [row for row in rows if self._matches(row)]
        if self.order_by is not None:
            selected = sorted(
                selected,
                key=lambda row: row.get(self.order_by) or "",
                reverse=self.order_desc,
            )
        if self.row_limit is not None:
            selected = selected[: self.row_limit]
        return FakeResult(selected)

    def _matches(self, row):
        return all(row.get(column) == value for column, value in self.filters)


class FakeSupabaseClient:
    def __init__(self):
        self.database = {}

    def table(self, table_name):
        return FakeTableQuery(self.database, table_name)


def test_persist_import_observations_stores_every_source_row_with_batch_metadata():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    observations = [
        {
            "date": "2025-06-10",
            "item_id": 1,
            "item_name": "Paneer",
            "current_stock": 12.0,
            "unit": "kg",
            "usage_value": 2.0,
            "usage_period": "daily",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.1,
            "category": "Dairy",
            "subcategory": "Cheese",
            "supplier_name": "Supplier A",
            "recent_waste_percentage": 4.0,
        },
        {
            "date": "2025-06-11",
            "item_id": 1,
            "item_name": "Paneer",
            "current_stock": 9.0,
            "unit": "kg",
            "usage_value": 3.0,
            "usage_period": "daily",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.1,
            "category": "Dairy",
            "subcategory": "Cheese",
            "supplier_name": "Supplier A",
            "recent_waste_percentage": 4.0,
        },
        {
            "date": "2025-06-12",
            "item_id": 2,
            "item_name": "Rice",
            "current_stock": 20.0,
            "unit": "kg",
            "usage_value": 2.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 70.0,
            "seasonal_factor": 1.0,
            "category": "Grain",
            "subcategory": "Staple",
            "supplier_name": "Supplier B",
            "recent_waste_percentage": 1.5,
        },
    ]

    result = store.persist_observations(
        observations,
        source_type="import",
        file_name="historical_inventory.csv",
        file_type="csv",
    )

    batch = client.database["import_batches"][0]
    records = client.database["inventory_records"]
    assert result["successful_rows"] == 3
    assert result["failed_rows"] == 0
    assert batch["file_name"] == "historical_inventory.csv"
    assert batch["file_type"] == "csv"
    assert batch["status"] == "success"
    assert batch["total_rows"] == 3
    assert batch["successful_rows"] == 3
    assert len(records) == 3
    assert [record["record_date"] for record in records] == [
        "2025-06-10",
        "2025-06-11",
        "2025-06-12",
    ]
    assert {record["input_source"] for record in records} == {"import"}
    assert all(record["import_batch_id"] == batch["import_batch_id"] for record in records)
    assert result["latest_records_by_history_identity"]["id:1"]["item_id"] == records[0]["item_id"]
    assert result["latest_records_by_history_identity"]["id:1"]["record_id"] == records[1]["record_id"]
    assert result["latest_records_by_history_identity"]["id:2"]["record_id"] == records[2]["record_id"]


def test_persist_manual_observations_uses_manual_source_without_import_batch():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    result = store.persist_observations(
        [
            {
                "date": "2025-06-12",
                "item_name": "Milk",
                "current_stock": 5.0,
                "unit": "litre",
                "usage_value": 4.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 8.0,
                "seasonal_factor": 1.0,
                "perishability_level": "medium",
            }
        ],
        source_type="manual",
    )

    records = client.database["inventory_records"]
    assert result["successful_rows"] == 1
    assert "import_batches" not in client.database
    assert records[0]["record_date"] == "2025-06-12"
    assert records[0]["input_source"] == "manual"
    assert records[0]["import_batch_id"] is None


def test_persist_observations_matches_items_by_owner_identity_not_name_only():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    store.persist_observations(
        [
            {
                "date": "2025-06-12",
                "item_name": "Milk",
                "current_stock": 5.0,
                "unit": "litre",
                "usage_value": 4.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 8.0,
                "seasonal_factor": 1.0,
                "category": "Dairy",
                "subcategory": "Fresh",
                "perishability_level": "medium",
            },
            {
                "date": "2025-06-12",
                "item_name": "Milk",
                "current_stock": 10.0,
                "unit": "carton",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 20.0,
                "seasonal_factor": 1.0,
                "category": "Dairy",
                "subcategory": "Bulk",
                "perishability_level": "medium",
            },
        ],
        source_type="manual",
    )

    assert len(client.database["items"]) == 2
    assert {item["unit"] for item in client.database["items"]} == {"litre", "carton"}


def test_persist_observations_scopes_items_and_suppliers_to_owner():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    observation = {
        "date": "2025-06-12",
        "item_name": "Milk",
        "current_stock": 5.0,
        "unit": "litre",
        "usage_value": 4.0,
        "usage_period": "daily",
        "lead_time_days": 2,
        "price_per_unit": 8.0,
        "seasonal_factor": 1.0,
        "category": "Dairy",
        "subcategory": "Fresh",
        "supplier_name": "Supplier A",
        "perishability_level": "medium",
    }

    store.persist_observations(
        [observation],
        source_type="manual",
        created_by="user-1",
        uploaded_by="user-1",
    )
    store.persist_observations(
        [observation],
        source_type="manual",
        created_by="user-2",
        uploaded_by="user-2",
    )

    assert len(client.database["items"]) == 2
    assert {item["owner_id"] for item in client.database["items"]} == {"user-1", "user-2"}
    assert len(client.database["suppliers"]) == 2
    assert {supplier["owner_id"] for supplier in client.database["suppliers"]} == {"user-1", "user-2"}


def test_list_user_observations_returns_only_that_users_rows():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    store.persist_observations(
        [
            {
                "date": "2025-06-10",
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-06-11",
                "item_name": "Paneer",
                "current_stock": 9.0,
                "unit": "kg",
                "usage_value": 3.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
        ],
        source_type="manual",
        created_by="user-1",
        uploaded_by="user-1",
    )
    store.persist_observations(
        [
            {
                "date": "2025-06-12",
                "item_name": "Rice",
                "current_stock": 20.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 70.0,
                "seasonal_factor": 1.0,
                "category": "Grain",
                "subcategory": "Staple",
                "supplier_name": "Supplier B",
                "recent_waste_percentage": 1.5,
            }
        ],
        source_type="manual",
        created_by="user-2",
        uploaded_by="user-2",
    )

    observations = store.list_user_observations("user-1")

    assert len(observations) == 2
    assert {observation["item_name"] for observation in observations} == {"Paneer"}
    assert all(observation["supplier_name"] == "Supplier A" for observation in observations)
    assert [observation["date"] for observation in observations] == ["2025-06-10", "2025-06-11"]


def _ranked_items():
    return [
        {
            "item_id": 1,
            "date": "2025-06-12",
            "item_name": "Paneer",
            "category": "Dairy",
            "subcategory": "Cheese",
            "unit": "kg",
            "supplier_name": "Supplier A",
            "current_stock": 5.0,
            "reorder_level": 8.0,
            "daily_usage": 4.0,
            "lead_time": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.1,
            "waste_percentage": 4.0,
            "avg_usage_7d": 3.0,
            "trend_direction": "up",
            "days_of_cover": 1.25,
            "inventory_value": 2250.0,
            "estimated_waste_cost": 90.0,
            "lead_time_demand": 13.2,
            "stock_gap_to_lead_demand": -8.2,
            "reorder_urgency_score": 88,
            "waste_risk_score": 42,
            "recommended_action": "RESTOCK_NOW",
            "_score_context": {
                "max_daily_usage": 4.0,
                "max_lead_time": 3,
                "max_waste_percentage": 4.0,
                "max_inventory_value": 2250.0,
            },
        },
        {
            "item_id": 2,
            "date": "2025-06-12",
            "item_name": "Rice",
            "category": "Grain",
            "subcategory": "Staple",
            "unit": "kg",
            "supplier_name": "Supplier B",
            "current_stock": 20.0,
            "reorder_level": 6.0,
            "daily_usage": 2.0,
            "lead_time": 2,
            "price_per_unit": 70.0,
            "seasonal_factor": 1.0,
            "waste_percentage": 1.5,
            "avg_usage_7d": 2.0,
            "trend_direction": "stable",
            "days_of_cover": 10.0,
            "inventory_value": 1400.0,
            "estimated_waste_cost": 21.0,
            "lead_time_demand": 4.0,
            "stock_gap_to_lead_demand": 16.0,
            "reorder_urgency_score": 15,
            "waste_risk_score": 35,
            "recommended_action": "DELAY_PURCHASE",
            "_score_context": {
                "max_daily_usage": 4.0,
                "max_lead_time": 3,
                "max_waste_percentage": 4.0,
                "max_inventory_value": 2250.0,
            },
        },
    ]


def test_create_analysis_snapshot_persists_run_and_ranked_results():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    analysis_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id="import_batches-1",
    )

    run = client.database["analysis_runs"][0]
    results = client.database["analysis_item_results"]
    assert analysis_id == run["analysis_id"]
    assert run["import_batch_id"] == "import_batches-1"
    assert run["source_type"] == "import"
    assert run["observation_count"] == 4
    assert run["item_count"] == 2
    assert run["date_range_start"] == "2025-06-10"
    assert run["date_range_end"] == "2025-06-12"
    assert len(results) == 2
    assert [result["rank_position"] for result in results] == [1, 2]
    assert [result["app_item_id"] for result in results] == [1, 2]
    assert results[0]["analysis_id"] == analysis_id
    assert results[0]["recommended_action"] == "RESTOCK_NOW"


def test_get_analysis_snapshot_rebuilds_analysis_record():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    analysis_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id=None,
    )

    record = store.get(analysis_id)

    assert record.dataset_summary["row_count"] == 4
    assert record.dataset_summary["item_count"] == 2
    assert record.dataset_summary["date_range"]["end"] == "2025-06-12"
    assert record.kpi_summary["item_count"] == 2
    assert record.kpi_summary["restock_now_count"] == 1
    assert len(record.items) == 2
    assert record.items[0]["item_id"] == 1
    assert record.items[0]["item_name"] == "Paneer"
    assert record.items[0]["recommended_action"] == "RESTOCK_NOW"


def test_get_analysis_snapshot_includes_source_observations_for_owner():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    store.persist_observations(
        [
            {
                "date": "2025-06-10",
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-07-10",
                "item_name": "Paneer",
                "current_stock": 4.0,
                "unit": "kg",
                "usage_value": 5.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
        ],
        source_type="import",
        created_by="user-1",
        uploaded_by="user-1",
    )
    store.persist_observations(
        [
            {
                "date": "2025-07-10",
                "item_name": "Rice",
                "current_stock": 18.0,
                "unit": "kg",
                "usage_value": 3.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 70.0,
                "seasonal_factor": 1.0,
                "category": "Grain",
                "subcategory": "Staple",
                "supplier_name": "Supplier B",
                "recent_waste_percentage": 1.5,
            }
        ],
        source_type="import",
        created_by="user-2",
        uploaded_by="user-2",
    )
    analysis_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 2,
            "item_count": 1,
            "date_range": {"start": "2025-06-10", "end": "2025-07-10"},
        },
        ranked_items=_ranked_items()[:1],
        source_type="import",
        created_by="user-1",
    )

    record = store.get(analysis_id, user_id="user-1")

    assert len(record.items) == 1
    assert len(record.source_observations) == 2
    assert [observation["date"] for observation in record.source_observations] == [
        "2025-06-10",
        "2025-07-10",
    ]
    assert {observation["item_name"] for observation in record.source_observations} == {"Paneer"}


def test_create_analysis_snapshot_persists_and_reads_exact_source_observations():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    source_observations = [
        {
            "date": "2025-06-10",
            "item_id": 1,
            "item_name": "Paneer",
            "current_stock": 12.0,
            "unit": "kg",
            "usage_value": 2.0,
            "usage_period": "daily",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.1,
            "category": "Dairy",
            "subcategory": "Cheese",
            "supplier_name": "Supplier A",
            "recent_waste_percentage": 4.0,
        },
        {
            "date": "2025-09-17",
            "item_id": 1,
            "item_name": "Paneer",
            "current_stock": 7.0,
            "unit": "kg",
            "usage_value": 5.0,
            "usage_period": "daily",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.1,
            "category": "Dairy",
            "subcategory": "Cheese",
            "supplier_name": "Supplier A",
            "recent_waste_percentage": 4.0,
        },
    ]

    analysis_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 2,
            "item_count": 1,
            "date_range": {"start": "2025-06-10", "end": "2025-09-17"},
        },
        ranked_items=_ranked_items()[:1],
        source_type="import",
        created_by="user-1",
        source_observations=source_observations,
    )
    client.database["inventory_records"] = []

    record = store.get(analysis_id, user_id="user-1")

    assert record.source_observations == source_observations


def test_get_analysis_snapshot_recovers_source_observations_from_owned_import_batch():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    persistence = store.persist_observations(
        [
            {
                "date": "2025-06-10",
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-07-10",
                "item_name": "Paneer",
                "current_stock": 4.0,
                "unit": "kg",
                "usage_value": 5.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
        ],
        source_type="import",
        created_by="user-1",
        uploaded_by="user-1",
    )
    for record in client.database["inventory_records"]:
        record["created_by"] = None

    analysis_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 2,
            "item_count": 1,
            "date_range": {"start": "2025-06-10", "end": "2025-07-10"},
        },
        ranked_items=_ranked_items()[:1],
        source_type="import",
        import_batch_id=persistence["import_batch_id"],
        created_by="user-1",
    )

    record = store.get(analysis_id, user_id="user-1")

    assert len(record.source_observations) == 2
    assert [observation["date"] for observation in record.source_observations] == [
        "2025-06-10",
        "2025-07-10",
    ]


def test_get_latest_analysis_id_returns_most_recent_snapshot():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)
    older_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id=None,
    )
    newer_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-13", "end": "2025-06-15"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id=None,
    )
    client.database["analysis_runs"][0]["created_at"] = "2025-06-12T00:00:00+00:00"
    client.database["analysis_runs"][1]["created_at"] = "2025-06-15T00:00:00+00:00"

    assert older_id != newer_id
    assert store.get_latest_analysis_id() == newer_id


def test_get_latest_analysis_id_filters_by_owner():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    older_user_1 = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        created_by="user-1",
    )
    store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="manual",
        created_by="user-2",
    )
    newer_user_1 = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 5,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-13"},
        },
        ranked_items=_ranked_items(),
        source_type="manual",
        created_by="user-1",
    )

    client.database["analysis_runs"][0]["created_at"] = "2025-06-12T00:00:00+00:00"
    client.database["analysis_runs"][1]["created_at"] = "2025-06-13T00:00:00+00:00"
    client.database["analysis_runs"][2]["created_at"] = "2025-06-14T00:00:00+00:00"

    assert older_user_1 != newer_user_1
    assert store.get_latest_analysis_id("user-1") == newer_user_1
    assert store.get_latest_analysis_id("user-2") == client.database["analysis_runs"][1]["analysis_id"]


def test_get_latest_analysis_id_skips_newer_snapshots_without_results():
    client = FakeSupabaseClient()
    store = SupabaseAnalysisStore(client)

    older_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-10", "end": "2025-06-12"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id=None,
    )
    newer_id = store.create_analysis_snapshot(
        dataset_summary={
            "row_count": 4,
            "item_count": 2,
            "date_range": {"start": "2025-06-13", "end": "2025-06-15"},
        },
        ranked_items=_ranked_items(),
        source_type="import",
        import_batch_id=None,
    )
    client.database["analysis_runs"][0]["created_at"] = "2025-06-12T00:00:00+00:00"
    client.database["analysis_runs"][1]["created_at"] = "2025-06-15T00:00:00+00:00"
    client.database["analysis_item_results"] = [
        row for row in client.database["analysis_item_results"] if row["analysis_id"] != newer_id
    ]

    assert store.get_latest_analysis_id() == older_id
