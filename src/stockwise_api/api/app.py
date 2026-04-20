from dataclasses import asdict, is_dataclass
from datetime import date

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from stockwise_api.schemas import (
    AnalysisResponse,
    ErrorEnvelope,
    ExplanationRequest,
    ExplanationResponse,
    ManualAnalysisRequest,
    RecordItem,
    SimulationRequest,
    SimulationResponse,
    RecordUpdateRequest,
    RecordsResponse,
)
from stockwise_api.services.glm import build_explanation_context, provider_from_env
from stockwise_api.services.manual_input import (
    ManualInputValidationError,
    item_to_record_view,
    normalize_item_history,
    normalize_manual_items,
)
from stockwise_api.services.parsing import ExplanationValidationError, build_fallback_explanation, parse_explanation_response
from stockwise_api.services.recommendations import build_kpi_summary, build_ranked_analysis
from stockwise_api.services.simulation import simulate_item_quantity
from stockwise_api.services.validation import (
    ValidationError,
    validate_inventory_csv,
    validate_manual_items,
)
from stockwise_api.store import InMemoryAnalysisStore


def _strip_internal_fields(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _safe_error(
    status_code: int, error_code: str, message: str, details=None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(
            error_code=error_code, message=message, details=details
        ).model_dump(),
    )


def _analysis_payload(store, analysis_id: str) -> dict:
    record = store.get(analysis_id)
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [_strip_internal_fields(item) for item in record.items],
    }


def _records_payload(store, analysis_id: str) -> dict:
    record = store.get(analysis_id)
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [item_to_record_view(item) for item in record.items],
    }


def _date_range_from_manual_items(items: list[dict]) -> dict:
    today = date.today().isoformat()
    dates = sorted(str(item.get("date") or today) for item in items)
    return {
        "start": dates[0] if dates else today,
        "end": dates[-1] if dates else today,
    }


def _save_analysis(store, items: list[dict], dataset_summary: dict, analysis_id: str | None = None) -> str:
    ranked_items = build_ranked_analysis(items)
    kpis = build_kpi_summary(ranked_items)
    if analysis_id is None:
        return store.create(dataset_summary=dataset_summary, kpi_summary=kpis, items=ranked_items)
    store.update(analysis_id=analysis_id, dataset_summary=dataset_summary, kpi_summary=kpis, items=ranked_items)
    return analysis_id


def create_app(glm_provider=None) -> FastAPI:
    app = FastAPI(title="StockWise Backend", version="0.1.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.store = InMemoryAnalysisStore()
    app.state.glm_provider = glm_provider or provider_from_env()

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError):
        return _safe_error(400, "validation_error", str(exc))

    @app.exception_handler(ManualInputValidationError)
    async def handle_manual_input_validation_error(_: Request, exc: ManualInputValidationError):
        return _safe_error(400, "manual_input_validation_error", str(exc))

    @app.exception_handler(ExplanationValidationError)
    async def handle_explanation_validation_error(
        _: Request, exc: ExplanationValidationError
    ):
        return _safe_error(400, "explanation_validation_error", str(exc))

    @app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
    async def get_analysis(analysis_id: str):
        # 1. Try to fetch the analysis from your in-memory store
        analysis = app.state.store.get(analysis_id)

        # 2. If it doesn't exist, throw the 404 error
        if not analysis:
            raise HTTPException(
                status_code=404, detail=f"Analysis {analysis_id} not found."
            )

        # 3. Format the response to match your schema
        # We use the same _strip_internal_fields logic you used in the POST method
        return {
            "analysis_id": analysis_id,
            "dataset_summary": analysis.dataset_summary,
            "kpi_summary": analysis.kpi_summary,
            "items": [_strip_internal_fields(item) for item in analysis.items],
        }

    @app.get("/api/v1/analyses/{analysis_id}/records")
    async def get_analysis_records(analysis_id: str):
        # 1. Fetch the analysis from the store
        analysis = app.state.store.get(analysis_id)

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis records not found.")

        # 2. Return the items list
        # Ensure we use the same _strip_internal_fields logic to keep the data clean
        return [_strip_internal_fields(item) for item in analysis.items]

    @app.post("/api/v1/analyses", response_model=AnalysisResponse)
    async def create_analysis(file: UploadFile = File(...)):
        raw = await file.read()
        validated_rows, summary = validate_inventory_csv(raw)
        normalized_items = normalize_item_history(validated_rows, preserve_item_ids=True)
        dataset_summary = asdict(summary)
        dataset_summary["item_count"] = len(normalized_items)
        analysis_id = _save_analysis(app.state.store, normalized_items, dataset_summary)
        return _analysis_payload(app.state.store, analysis_id)

    @app.post("/api/v1/manual-analyses", response_model=AnalysisResponse)
    async def create_manual_analysis(request: ManualAnalysisRequest):
        raw_items = [item.model_dump() for item in request.items]
        normalized_items = normalize_item_history(raw_items, preserve_item_ids=True)
        dataset_summary = {
            "row_count": len(raw_items),
            "item_count": len(normalized_items),
            "date_range": _date_range_from_manual_items(raw_items),
        }
        analysis_id = _save_analysis(app.state.store, normalized_items, dataset_summary)
        return _analysis_payload(app.state.store, analysis_id)

    @app.get("/api/v1/analyses/{analysis_id}/records", response_model=RecordsResponse)
    async def get_records(analysis_id: str):
        try:
            return _records_payload(app.state.store, analysis_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/v1/manual-analyses", response_model=AnalysisResponse)
    async def create_manual_analysis(items: list[ManualItemInput]):
        item_dicts = [item.model_dump() for item in items]
        normalized, summary = validate_manual_items(item_dicts)
        metrics = build_item_metrics(normalized)
        ranked_items = build_ranked_analysis(metrics)
        kpis = build_kpi_summary(ranked_items)
        analysis_id = app.state.store.create(
            dataset_summary=asdict(summary),
            kpi_summary=kpis,
            items=ranked_items,
        )
        return {
            "analysis_id": analysis_id,
            "dataset_summary": asdict(summary),
            "kpi_summary": kpis,
            "items": [_strip_internal_fields(item) for item in ranked_items],
        }

    @app.post(
        "/api/v1/analyses/{analysis_id}/items/{item_id}/simulate",
        response_model=SimulationResponse,
    )
    async def simulate_item(analysis_id: str, item_id: int, request: SimulationRequest):
        try:
            item = app.state.store.get_item(analysis_id, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        simulated = simulate_item_quantity(item, request.simulated_order_qty)
        return simulated

<<<<<<< HEAD
    @app.post(
        "/api/v1/analyses/{analysis_id}/items/{item_id}/explanation",
        response_model=ExplanationResponse,
    )
=======
    @app.patch("/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordItem)
    async def update_record(analysis_id: str, item_id: int, request: RecordUpdateRequest):
        try:
            record = app.state.store.get(analysis_id)
            existing_item = app.state.store.get_item(analysis_id, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        editable = item_to_record_view(existing_item)
        editable["date"] = existing_item["date"]
        editable["item_id"] = existing_item["item_id"]
        patch = request.model_dump(exclude_none=True)
        editable.update(patch)
        normalized_item = normalize_manual_items([editable], preserve_item_ids=True)[0]
        normalized_item["_observation_count"] = int(existing_item.get("_observation_count", 1))
        updated_items = [
            normalized_item if int(item["item_id"]) == int(item_id) else item
            for item in record.items
        ]
        dataset_summary = {
            **record.dataset_summary,
            "item_count": len(updated_items),
        }
        _save_analysis(app.state.store, updated_items, dataset_summary, analysis_id=analysis_id)
        updated_item = app.state.store.get_item(analysis_id, item_id)
        return item_to_record_view(updated_item)

    @app.delete("/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordsResponse)
    async def delete_record(analysis_id: str, item_id: int):
        try:
            record = app.state.store.get(analysis_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        remaining_items = [item for item in record.items if int(item["item_id"]) != int(item_id)]
        if len(remaining_items) == len(record.items):
            raise HTTPException(status_code=404, detail=f"Unknown item_id: {item_id}")
        if not remaining_items:
            raise HTTPException(status_code=400, detail="Cannot delete the last remaining item in the analysis.")
        removed_item = next(item for item in record.items if int(item["item_id"]) == int(item_id))
        remaining_row_count = max(
            len(remaining_items),
            int(record.dataset_summary.get("row_count", len(record.items)))
            - int(removed_item.get("_observation_count", 1)),
        )
        dataset_summary = {
            **record.dataset_summary,
            "row_count": remaining_row_count,
            "item_count": len(remaining_items),
        }
        _save_analysis(app.state.store, remaining_items, dataset_summary, analysis_id=analysis_id)
        return _records_payload(app.state.store, analysis_id)

    @app.post("/api/v1/analyses/{analysis_id}/items/{item_id}/explanation", response_model=ExplanationResponse)
>>>>>>> 066dd37 (feat: add contracts and manual input validation updates)
    async def explain_item(analysis_id: str, item_id: int, request: ExplanationRequest):
        try:
            item = app.state.store.get_item(analysis_id, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        simulation_context = None
        if request.simulated_order_qty is not None:
            simulation = simulate_item_quantity(item, request.simulated_order_qty)
            simulation_context = {
                "simulated_order_qty": simulation["simulated_order_qty"],
                "simulated_cash_outlay": simulation["simulated_cash_outlay"],
                "simulated_coverage_days": simulation["simulated_coverage_days"],
                "simulated_risk_change": simulation["simulated_risk_change"],
            }

        context = build_explanation_context(item, simulation_context=simulation_context)
        provider = app.state.glm_provider

        try:
            raw = provider.generate_explanation(context)
            parsed = parse_explanation_response(raw, context)
            return {"source": provider.source, **parsed}
        except ExplanationValidationError:
            try:
                strict_context = {**context, "_strict_json": True}
                raw = provider.generate_explanation(strict_context)
                parsed = parse_explanation_response(raw, context)
                return {"source": provider.source, **parsed}
            except Exception:
                return build_fallback_explanation(context)
        except Exception:
            return build_fallback_explanation(context)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException):
        details = exc.detail
        message = details if isinstance(details, str) else "Request failed."
        return _safe_error(exc.status_code, "request_error", message, details=details)

    return app
