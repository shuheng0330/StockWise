from dataclasses import dataclass
from uuid import uuid4


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
