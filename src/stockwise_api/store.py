from dataclasses import dataclass
from uuid import uuid4
from typing import Optional
from supabase import Client
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRecord:
    dataset_summary: dict
    kpi_summary: dict
    items: list[dict]


class InMemoryAnalysisStore:
    def __init__(self) -> None:
        self._records: dict[str, AnalysisRecord] = {}

    def create(self, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> str:
        analysis_id = str(uuid4())
        self._records[analysis_id] = AnalysisRecord(
            dataset_summary=dataset_summary,
            kpi_summary=kpi_summary,
            items=items,
        )
        return analysis_id

    def get(self, analysis_id: str) -> AnalysisRecord:
        try:
            return self._records[analysis_id]
        except KeyError as exc:
            raise KeyError(f"Unknown analysis_id: {analysis_id}") from exc

    def get_item(self, analysis_id: str, item_id: int) -> dict:
        record = self.get(analysis_id)
        for item in record.items:
            if int(item["item_id"]) == int(item_id):
                return item
        raise KeyError(f"Unknown item_id: {item_id}")

    def update(self, analysis_id: str, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> AnalysisRecord:
        record = self.get(analysis_id)
        record.dataset_summary = dataset_summary
        record.kpi_summary = kpi_summary
        record.items = items
        return record


class SupabaseAnalysisStore:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def create(self, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> str:
        analysis_id = str(uuid4())
        successful_items = 0
        failed_items = 0

        try:
            # Create import batch record
            import_batch = {
                "file_name": f"analysis_{analysis_id}",
                "file_type": "analysis",
                "status": "pending",
                "total_rows": len(items),
                "successful_rows": 0,
                "failed_rows": 0
            }

            batch_result = self.supabase.table("import_batches").insert(import_batch).execute()
            import_batch_id = batch_result.data[0]["import_batch_id"]
            logger.info(f"Created import batch: {import_batch_id}")

            # Process items and inventory records
            for idx, item in enumerate(items):
                try:
                    # Validate subcategory
                    if not item.get("subcategory"):
                        logger.warning(f"Missing subcategory for item: {item.get('item_name')}")

                    # Validate supplier_name
                    if not item.get("supplier_name"):
                        logger.warning(f"Missing supplier_name for item: {item.get('item_name')}")

                    # Ensure supplier exists
                    supplier_id = None
                    if item.get("supplier_name"):
                        supplier_result = self.supabase.table("suppliers").select("supplier_id").eq("supplier_name", item["supplier_name"]).execute()
                        if supplier_result.data:
                            supplier_id = supplier_result.data[0]["supplier_id"]
                            logger.info(f"Supplier already exists: {item['supplier_name']} with id {supplier_id}")
                        else:
                            supplier_data = {"supplier_name": item["supplier_name"]}
                            supplier_insert_result = self.supabase.table("suppliers").insert(supplier_data).execute()
                            supplier_id = supplier_insert_result.data[0]["supplier_id"]
                            logger.info(f"Created new supplier: {item['supplier_name']} with id {supplier_id}")

                    # Ensure item exists
                    item_data = {
                        "item_name": item["item_name"],
                        "category": item.get("category"),
                        "subcategory": item.get("subcategory"),
                        "unit": item.get("unit", "pieces"),
                        "supplier_id": supplier_id
                    }

                    # Check if item already exists
                    try:
                        existing_item = self.supabase.table("items").select("item_id").eq("item_name", item["item_name"]).execute()
                        if existing_item.data:
                            item_id = existing_item.data[0]["item_id"]
                            logger.info(f"Item already exists: {item['item_name']} with id {item_id}")
                        else:
                            item_result = self.supabase.table("items").insert(item_data).execute()
                            item_id = item_result.data[0]["item_id"]
                            logger.info(f"Created new item: {item['item_name']} with id {item_id}")
                    except Exception as e:
                        logger.error(f"Error creating/checking item {item.get('item_name')}: {e}")
                        failed_items += 1
                        continue

                    # Create inventory record
                    record_data = {
                        "record_date": item.get("record_date", "2024-01-01"),
                        "item_id": item_id,
                        "current_stock": float(item["current_stock"]),
                        "reorder_level": float(item["reorder_level"]),
                        "daily_usage": float(item["daily_usage"]),
                        "lead_time": int(item["lead_time"]),
                        "price_per_unit": float(item["price_per_unit"]),
                        "seasonal_factor": float(item.get("seasonal_factor", 1.0)),
                        "waste_percentage": float(item.get("waste_percentage", 0)),
                        "input_source": "import",
                        "import_batch_id": import_batch_id
                    }

                    try:
                        self.supabase.table("inventory_records").insert(record_data).execute()
                        logger.info(f"Created inventory record for item {item_id}")
                        successful_items += 1
                    except Exception as e:
                        logger.error(f"Error creating inventory record for item {item_id}: {e}")
                        failed_items += 1
                        continue

                    # Store the Supabase item_id separately without overwriting the integer item_id
                    item["_supabase_item_id"] = str(item_id)

                except Exception as e:
                    logger.error(f"Error processing item {idx}: {e}")
                    failed_items += 1
                    continue

            # Update import batch status
            try:
                self.supabase.table("import_batches").update({
                    "status": "success" if failed_items == 0 else "partial",
                    "successful_rows": successful_items,
                    "failed_rows": failed_items
                }).eq("import_batch_id", import_batch_id).execute()
                logger.info(f"Updated import batch {import_batch_id}: {successful_items} successful, {failed_items} failed")
            except Exception as e:
                logger.error(f"Error updating import batch status: {e}")

        except Exception as e:
            logger.error(f"Error in Supabase store create: {e}")

        # Store analysis record in memory for now (could also persist this)
        record = AnalysisRecord(
            dataset_summary=dataset_summary,
            kpi_summary=kpi_summary,
            items=items,
        )

        # For now, return the analysis_id - in a full implementation, 
        # you'd want to persist the analysis metadata too
        return analysis_id

    def get(self, analysis_id: str) -> AnalysisRecord:
        # For now, this is a placeholder - you'd need to implement 
        # retrieving analysis data from the database
        # This would involve querying the item_decision_metrics view
        raise NotImplementedError("Supabase store get method not fully implemented")

    def get_item(self, analysis_id: str, item_id: int) -> dict:
        # Query the item_decision_metrics view for the specific item
        result = self.supabase.table("item_decision_metrics").select("*").eq("item_id", item_id).execute()
        if result.data:
            return result.data[0]
        raise KeyError(f"Unknown item_id: {item_id}")

    def update(self, analysis_id: str, dataset_summary: dict, kpi_summary: dict, items: list[dict]) -> AnalysisRecord:
        # Placeholder - would need to implement update logic
        raise NotImplementedError("Supabase store update method not implemented")
