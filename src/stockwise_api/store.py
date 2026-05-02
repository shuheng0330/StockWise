import logging
from dataclasses import dataclass, field
from uuid import uuid4

from supabase import Client

from stockwise_api.services.recommendations import build_kpi_summary
from stockwise_api.services.manual_input import normalize_manual_items

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRecord:
    dataset_summary: dict
    kpi_summary: dict
    items: list[dict]
    source_observations: list[dict] = field(default_factory=list)


class InMemoryAnalysisStore:
    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}
        self._owners: dict[str, str | None] = {}

    def create(
        self,
        dataset_summary: dict,
        kpi_summary: dict,
        items: list[dict],
        analysis_id: str | None = None,
        owner_id: str | None = None,
        source_observations: list[dict] | None = None,
    ) -> str:
        analysis_id = analysis_id or str(uuid4())
        self._records[analysis_id] = AnalysisRecord(
            dataset_summary=dataset_summary,
            kpi_summary=kpi_summary,
            items=items,
            source_observations=source_observations or [],
        )
        self._owners[analysis_id] = owner_id
        return analysis_id

    def get(self, analysis_id: str, owner_id: str | None = None) -> AnalysisRecord:
        try:
            record = self._records[analysis_id]
        except KeyError as exc:
            raise KeyError(f"Unknown analysis_id: {analysis_id}") from exc
        stored_owner_id = self._owners.get(analysis_id)
        if owner_id is not None and stored_owner_id is not None and stored_owner_id != owner_id:
            raise KeyError(f"Unknown analysis_id: {analysis_id}")
        return record

    def get_item(self, analysis_id: str, item_id: int, owner_id: str | None = None) -> dict:
        record = self.get(analysis_id, owner_id=owner_id)
        for item in record.items:
            if int(item["item_id"]) == int(item_id):
                return item
        raise KeyError(f"Unknown item_id: {item_id}")

    def update(
        self,
        analysis_id: str,
        dataset_summary: dict,
        kpi_summary: dict,
        items: list[dict],
        owner_id: str | None = None,
        source_observations: list[dict] | None = None,
    ) -> AnalysisRecord:
        record = self.get(analysis_id, owner_id=owner_id)
        record.dataset_summary = dataset_summary
        record.kpi_summary = kpi_summary
        record.items = items
        if source_observations is not None:
            record.source_observations = source_observations
        return record

    def get_latest_analysis_id(self, owner_id: str | None = None) -> str:
        for analysis_id in reversed(list(self._records.keys())):
            stored_owner_id = self._owners.get(analysis_id)
            if owner_id is not None and stored_owner_id is not None and stored_owner_id != owner_id:
                continue
            return analysis_id
        raise KeyError("No in-memory analyses found.")


class SupabaseAnalysisStore:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def persist_observations(
        self,
        observations: list[dict],
        *,
        source_type: str,
        file_name: str | None = None,
        file_type: str | None = None,
        uploaded_by: str | None = None,
        created_by: str | None = None,
    ) -> dict:
        if source_type not in {"manual", "import"}:
            raise ValueError("source_type must be 'manual' or 'import'.")

        normalized_observations = normalize_manual_items(observations)
        import_batch_id = None
        successful_rows = 0
        failed_rows = 0
        latest_records_by_history_identity: dict[str, dict] = {}
        owner_id = created_by or uploaded_by

        if source_type == "import":
            import_batch_id = self._create_import_batch(
                file_name=file_name,
                file_type=file_type,
                uploaded_by=uploaded_by,
                total_rows=len(observations),
            )

        for row_number, (raw_observation, observation) in enumerate(
            zip(observations, normalized_observations),
            start=1,
        ):
            try:
                supplier_id = self._find_or_create_supplier(
                    observation.get("supplier_name"),
                    owner_id=owner_id,
                )
                item_id = self._find_or_create_item(
                    observation,
                    supplier_id=supplier_id,
                    owner_id=owner_id,
                )
                record = self._inventory_record_payload(
                    observation,
                    item_id=item_id,
                    source_type=source_type,
                    import_batch_id=import_batch_id,
                    created_by=created_by,
                )
                record_result = self.supabase.table("inventory_records").insert(record).execute()
                inserted_record = record_result.data[0]
                history_identity = observation.get("_history_identity")
                if history_identity is not None:
                    latest_records_by_history_identity[history_identity] = {
                        "item_id": item_id,
                        "record_id": inserted_record["record_id"],
                    }
                successful_rows += 1
            except Exception as exc:
                failed_rows += 1
                logger.error("Failed to persist inventory observation row %s: %s", row_number, exc)
                if import_batch_id is not None:
                    self._record_import_row_error(
                        import_batch_id=import_batch_id,
                        row_number=row_number,
                        error_message=str(exc),
                        raw_data=raw_observation,
                    )

        if import_batch_id is not None:
            self._update_import_batch(
                import_batch_id=import_batch_id,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
            )

        return {
            "import_batch_id": import_batch_id,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "latest_records_by_history_identity": latest_records_by_history_identity,
        }

    def _create_import_batch(
        self,
        *,
        file_name: str | None,
        file_type: str | None,
        uploaded_by: str | None,
        total_rows: int,
    ) -> str:
        batch = {
            "file_name": file_name,
            "file_type": file_type,
            "uploaded_by": uploaded_by,
            "status": "pending",
            "total_rows": total_rows,
            "successful_rows": 0,
            "failed_rows": 0,
        }
        result = self.supabase.table("import_batches").insert(batch).execute()
        return result.data[0]["import_batch_id"]

    def _update_import_batch(self, *, import_batch_id: str, successful_rows: int, failed_rows: int) -> None:
        if failed_rows == 0:
            status = "success"
        elif successful_rows == 0:
            status = "failed"
        else:
            status = "partial"

        self.supabase.table("import_batches").update(
            {
                "status": status,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
            }
        ).eq("import_batch_id", import_batch_id).execute()

    def _record_import_row_error(
        self,
        *,
        import_batch_id: str,
        row_number: int,
        error_message: str,
        raw_data: dict,
    ) -> None:
        self.supabase.table("import_row_errors").insert(
            {
                "import_batch_id": import_batch_id,
                "row_number": row_number,
                "error_message": error_message,
                "raw_data": raw_data,
            }
        ).execute()

    def _find_or_create_supplier(self, supplier_name: str | None, *, owner_id: str | None) -> str | None:
        normalized_supplier = _normalize_optional_text(supplier_name)
        if normalized_supplier is None or normalized_supplier.lower() == "unknown":
            return None

        result = (
            self.supabase.table("suppliers")
            .select("supplier_id")
            .eq("supplier_name", normalized_supplier)
            .eq("owner_id", owner_id)
            .execute()
        )
        if result.data:
            return result.data[0]["supplier_id"]

        inserted = self.supabase.table("suppliers").insert(
            {"supplier_name": normalized_supplier, "owner_id": owner_id}
        ).execute()
        return inserted.data[0]["supplier_id"]

    def _find_or_create_item(self, item: dict, *, supplier_id: str | None, owner_id: str | None) -> str:
        item_identity = {
            "item_name": item["item_name"],
            "category": item.get("category"),
            "subcategory": item.get("subcategory"),
            "unit": item.get("unit"),
            "supplier_id": supplier_id,
            "owner_id": owner_id,
        }

        result = (
            self.supabase.table("items")
            .select("item_id,item_name,category,subcategory,unit,supplier_id,owner_id")
            .eq("item_name", item_identity["item_name"])
            .eq("owner_id", owner_id)
            .execute()
        )
        for existing_item in result.data:
            if _same_item_identity(existing_item, item_identity):
                return existing_item["item_id"]

        inserted = self.supabase.table("items").insert(item_identity).execute()
        return inserted.data[0]["item_id"]

    def _inventory_record_payload(
        self,
        item: dict,
        *,
        item_id: str,
        source_type: str,
        import_batch_id: str | None,
        created_by: str | None,
    ) -> dict:
        return {
            "record_date": item["date"],
            "item_id": item_id,
            "current_stock": float(item["current_stock"]),
            "reorder_level": float(item["reorder_level"]),
            "daily_usage": float(item["daily_usage"]),
            "lead_time": int(item["lead_time"]),
            "price_per_unit": float(item["price_per_unit"]),
            "seasonal_factor": float(item.get("seasonal_factor", 1.0)),
            "waste_percentage": float(item.get("waste_percentage", 0)),
            "input_source": source_type,
            "import_batch_id": import_batch_id,
            "created_by": created_by,
        }

    def create_analysis_snapshot(
        self,
        *,
        dataset_summary: dict,
        ranked_items: list[dict],
        source_type: str,
        import_batch_id: str | None = None,
        created_by: str | None = None,
        source_observations: list[dict] | None = None,
        formula_version: str = "stockwise-v1",
    ) -> str:
        if source_type not in {"manual", "import"}:
            raise ValueError("source_type must be 'manual' or 'import'.")

        date_range = dataset_summary.get("date_range", {})
        analysis_run = {
            "import_batch_id": import_batch_id,
            "source_type": source_type,
            "date_range_start": date_range.get("start"),
            "date_range_end": date_range.get("end"),
            "observation_count": int(dataset_summary.get("row_count", len(ranked_items))),
            "item_count": int(dataset_summary.get("item_count", len(ranked_items))),
            "formula_version": formula_version,
            "created_by": created_by,
        }
        run_result = self.supabase.table("analysis_runs").insert(analysis_run).execute()
        analysis_id = run_result.data[0]["analysis_id"]

        for rank_position, item in enumerate(ranked_items, start=1):
            self.supabase.table("analysis_item_results").insert(
                self._analysis_item_result_payload(
                    analysis_id=analysis_id,
                    rank_position=rank_position,
                    item=item,
                )
            ).execute()

        self._persist_analysis_source_observations(
            analysis_id=analysis_id,
            source_observations=source_observations or [],
        )

        return analysis_id

    def _persist_analysis_source_observations(
        self,
        *,
        analysis_id: str,
        source_observations: list[dict],
    ) -> None:
        rows = [
            {
                "analysis_id": analysis_id,
                "row_number": row_number,
                "observation_data": observation,
            }
            for row_number, observation in enumerate(source_observations, start=1)
        ]
        chunk_size = 500
        for start in range(0, len(rows), chunk_size):
            self.supabase.table("analysis_source_observations").insert(
                rows[start : start + chunk_size]
            ).execute()

    def _analysis_item_result_payload(self, *, analysis_id: str, rank_position: int, item: dict) -> dict:
        return {
            "analysis_id": analysis_id,
            "item_id": item.get("_supabase_item_id"),
            "latest_record_id": item.get("_latest_record_id"),
            "app_item_id": int(item["item_id"]),
            "latest_record_date": item["date"],
            "rank_position": rank_position,
            "item_name": item["item_name"],
            "category": item.get("category"),
            "subcategory": item.get("subcategory"),
            "unit": item["unit"],
            "supplier_name": item.get("supplier_name"),
            "current_stock": float(item["current_stock"]),
            "reorder_level": float(item["reorder_level"]),
            "daily_usage": float(item["daily_usage"]),
            "lead_time": int(item["lead_time"]),
            "price_per_unit": float(item["price_per_unit"]),
            "seasonal_factor": float(item["seasonal_factor"]),
            "waste_percentage": float(item["waste_percentage"]),
            "avg_usage_7d": float(item["avg_usage_7d"]),
            "trend_direction": item["trend_direction"],
            "days_of_cover": float(item["days_of_cover"]),
            "inventory_value": float(item["inventory_value"]),
            "estimated_waste_cost": float(item["estimated_waste_cost"]),
            "lead_time_demand": float(item["lead_time_demand"]),
            "stock_gap_to_lead_demand": float(item["stock_gap_to_lead_demand"]),
            "reorder_urgency_score": int(item["reorder_urgency_score"]),
            "waste_risk_score": int(item["waste_risk_score"]),
            "recommended_action": item["recommended_action"],
        }

    def create(self, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> str:
        analysis_id = str(uuid4())
        return analysis_id

    def get(self, analysis_id: str, user_id: str | None = None) -> AnalysisRecord:
        run_query = self.supabase.table("analysis_runs").select("*").eq("analysis_id", analysis_id)
        if user_id is not None:
            run_query = run_query.eq("created_by", user_id)
        run_result = run_query.execute()
        if not run_result.data:
            raise KeyError(f"Unknown analysis_id: {analysis_id}")

        item_result = (
            self.supabase.table("analysis_item_results")
            .select("*")
            .eq("analysis_id", analysis_id)
            .execute()
        )
        if not item_result.data:
            raise KeyError(f"Unknown analysis_id: {analysis_id}")
        items = [
            _analysis_item_from_result(row)
            for row in sorted(item_result.data, key=lambda row: int(row["rank_position"]))
        ]
        analysis_run = run_result.data[0]
        dataset_summary = {
            "row_count": int(analysis_run["observation_count"]),
            "item_count": int(analysis_run["item_count"]),
            "date_range": {
                "start": analysis_run.get("date_range_start"),
                "end": analysis_run.get("date_range_end"),
            },
        }
        source_observations = self._source_observations_for_analysis_run(
            analysis_run,
            user_id=user_id,
        )
        return AnalysisRecord(
            dataset_summary=dataset_summary,
            kpi_summary=build_kpi_summary(items),
            items=items,
            source_observations=source_observations,
        )

    def get_latest_analysis_id(self, user_id: str | None = None) -> str:
        query = self.supabase.table("analysis_runs").select("analysis_id")
        if user_id is not None:
            query = query.eq("created_by", user_id)
        result = query.order("created_at", desc=True).limit(20).execute()
        if not result.data:
            raise KeyError("No analysis snapshots found.")
        for row in result.data:
            analysis_id = str(row["analysis_id"])
            try:
                self.get(analysis_id, user_id=user_id)
                return analysis_id
            except KeyError:
                continue
        raise KeyError("No valid analysis snapshots found.")

    def list_user_observations(self, user_id: str) -> list[dict]:
        records = (
            self.supabase.table("inventory_records")
            .select("*")
            .eq("created_by", user_id)
            .order("record_date")
            .execute()
            .data
        )
        items = (
            self.supabase.table("items")
            .select("*")
            .eq("owner_id", user_id)
            .execute()
            .data
        )
        suppliers = (
            self.supabase.table("suppliers")
            .select("*")
            .eq("owner_id", user_id)
            .execute()
            .data
        )
        return _observations_from_records(records, items=items, suppliers=suppliers)

    def _source_observations_for_analysis_run(self, analysis_run: dict, *, user_id: str | None) -> list[dict]:
        snapshot_observations = self._snapshot_source_observations(str(analysis_run["analysis_id"]))
        if snapshot_observations:
            return snapshot_observations

        owner_id = user_id or analysis_run.get("created_by")
        if owner_id is None:
            return []

        start = analysis_run.get("date_range_start")
        end = analysis_run.get("date_range_end")
        observations = self.list_user_observations(str(owner_id))
        filtered_observations = [
            observation
            for observation in observations
            if _date_in_range(str(observation.get("date", "")), start=start, end=end)
        ]
        expected_count = int(analysis_run.get("observation_count") or 0)
        import_batch_id = analysis_run.get("import_batch_id")
        if len(filtered_observations) >= expected_count or not import_batch_id:
            return filtered_observations

        batch_observations = self._source_observations_for_import_batch(str(import_batch_id))
        filtered_batch_observations = [
            observation
            for observation in batch_observations
            if _date_in_range(str(observation.get("date", "")), start=start, end=end)
        ]
        if len(filtered_batch_observations) > len(filtered_observations):
            return filtered_batch_observations
        return filtered_observations

    def _snapshot_source_observations(self, analysis_id: str) -> list[dict]:
        try:
            rows = (
                self.supabase.table("analysis_source_observations")
                .select("*")
                .eq("analysis_id", analysis_id)
                .order("row_number")
                .execute()
                .data
            )
        except Exception:
            return []
        return [dict(row.get("observation_data") or {}) for row in rows]

    def _source_observations_for_import_batch(self, import_batch_id: str) -> list[dict]:
        records = (
            self.supabase.table("inventory_records")
            .select("*")
            .eq("import_batch_id", import_batch_id)
            .order("record_date")
            .execute()
            .data
        )
        items = self.supabase.table("items").select("*").execute().data
        suppliers = self.supabase.table("suppliers").select("*").execute().data
        return _observations_from_records(records, items=items, suppliers=suppliers)

    def get_item(self, analysis_id: str, item_id: int) -> dict:
        # Query the item_decision_metrics view for the specific item
        result = self.supabase.table("item_decision_metrics").select("*").eq("item_id", item_id).execute()
        if result.data:
            return result.data[0]
        raise KeyError(f"Unknown item_id: {item_id}")

    def update(self, analysis_id: str, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> AnalysisRecord:
        # Placeholder - would need to implement update logic
        raise NotImplementedError("Supabase store update method not implemented")


def _normalize_optional_text(value) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _identity_value(value) -> str:
    return str(value or "").strip().lower()


def _same_item_identity(existing_item: dict, item_identity: dict) -> bool:
    return (
        _identity_value(existing_item.get("item_name")) == _identity_value(item_identity.get("item_name"))
        and _identity_value(existing_item.get("unit")) == _identity_value(item_identity.get("unit"))
        and _identity_value(existing_item.get("category")) == _identity_value(item_identity.get("category"))
        and _identity_value(existing_item.get("subcategory")) == _identity_value(item_identity.get("subcategory"))
        and _identity_value(existing_item.get("supplier_id")) == _identity_value(item_identity.get("supplier_id"))
        and _identity_value(existing_item.get("owner_id")) == _identity_value(item_identity.get("owner_id"))
    )


def _history_identity_from_owner_fields(
    *,
    item_name: str | None,
    unit: str | None,
    category: str | None,
    subcategory: str | None,
) -> str:
    identity_parts = [
        str(item_name or "").strip().lower(),
        str(unit or "").strip().lower(),
        str(category or "").strip().lower(),
        str(subcategory or "").strip().lower(),
    ]
    return "item:" + "|".join(identity_parts)


def _observations_from_records(records: list[dict], *, items: list[dict], suppliers: list[dict]) -> list[dict]:
    items_by_id = {row["item_id"]: row for row in items}
    suppliers_by_id = {row["supplier_id"]: row for row in suppliers}

    observations: list[dict] = []
    for record in records:
        item = items_by_id.get(record.get("item_id"))
        if item is None:
            continue
        supplier = suppliers_by_id.get(item.get("supplier_id"))
        observations.append(
            {
                "date": str(record["record_date"]),
                "item_name": item["item_name"],
                "current_stock": float(record["current_stock"]),
                "unit": item["unit"],
                "usage_value": float(record["daily_usage"]),
                "usage_period": "daily",
                "lead_time_days": int(record["lead_time"]),
                "price_per_unit": float(record["price_per_unit"]),
                "seasonal_factor": float(record["seasonal_factor"]),
                "category": item.get("category"),
                "subcategory": item.get("subcategory"),
                "supplier_name": supplier.get("supplier_name") if supplier else None,
                "manual_reorder_level": float(record["reorder_level"]),
                "recent_waste_percentage": float(record["waste_percentage"]),
                "_history_identity": _history_identity_from_owner_fields(
                    item_name=item["item_name"],
                    unit=item.get("unit"),
                    category=item.get("category"),
                    subcategory=item.get("subcategory"),
                ),
                "_supabase_item_id": item["item_id"],
                "_latest_record_id": record["record_id"],
            }
        )
    return observations


def _date_in_range(value: str, *, start: str | None, end: str | None) -> bool:
    if start is not None and value < str(start):
        return False
    if end is not None and value > str(end):
        return False
    return True


def _analysis_item_from_result(row: dict) -> dict:
    return {
        "item_id": int(row["app_item_id"]),
        "date": str(row["latest_record_date"]),
        "item_name": row["item_name"],
        "category": row.get("category") or "Uncategorized",
        "subcategory": row.get("subcategory") or row.get("category") or "General",
        "unit": row["unit"],
        "supplier_name": row.get("supplier_name") or "Unknown",
        "current_stock": float(row["current_stock"]),
        "reorder_level": float(row["reorder_level"]),
        "daily_usage": float(row["daily_usage"]),
        "lead_time": int(row["lead_time"]),
        "price_per_unit": float(row["price_per_unit"]),
        "seasonal_factor": float(row["seasonal_factor"]),
        "waste_percentage": float(row["waste_percentage"]),
        "avg_usage_7d": float(row["avg_usage_7d"]),
        "trend_direction": row["trend_direction"],
        "days_of_cover": float(row["days_of_cover"]),
        "inventory_value": float(row["inventory_value"]),
        "estimated_waste_cost": float(row["estimated_waste_cost"]),
        "lead_time_demand": float(row["lead_time_demand"]),
        "stock_gap_to_lead_demand": float(row["stock_gap_to_lead_demand"]),
        "reorder_urgency_score": int(row["reorder_urgency_score"]),
        "waste_risk_score": int(row["waste_risk_score"]),
        "recommended_action": row["recommended_action"],
    }
