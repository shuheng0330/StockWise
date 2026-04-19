from dataclasses import asdict, is_dataclass

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from stockwise_api.schemas import (
    AnalysisResponse,
    ErrorEnvelope,
    ExplanationRequest,
    ExplanationResponse,
    SimulationRequest,
    SimulationResponse,
)
from stockwise_api.services.glm import build_explanation_context, provider_from_env
from stockwise_api.services.metrics import build_item_metrics
from stockwise_api.services.parsing import ExplanationValidationError, build_fallback_explanation, parse_explanation_response
from stockwise_api.services.recommendations import build_kpi_summary, build_ranked_analysis
from stockwise_api.services.simulation import simulate_item_quantity
from stockwise_api.services.validation import ValidationError, validate_inventory_csv
from stockwise_api.store import InMemoryAnalysisStore


def _strip_internal_fields(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _safe_error(status_code: int, error_code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(error_code=error_code, message=message, details=details).model_dump(),
    )


def create_app(glm_provider=None) -> FastAPI:
    app = FastAPI(title="StockWise Backend", version="0.1.0")
    app.state.store = InMemoryAnalysisStore()
    app.state.glm_provider = glm_provider or provider_from_env()

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError):
        return _safe_error(400, "validation_error", str(exc))

    @app.exception_handler(ExplanationValidationError)
    async def handle_explanation_validation_error(_: Request, exc: ExplanationValidationError):
        return _safe_error(400, "explanation_validation_error", str(exc))

    @app.post("/api/v1/analyses", response_model=AnalysisResponse)
    async def create_analysis(file: UploadFile = File(...)):
        raw = await file.read()
        normalized, summary = validate_inventory_csv(raw)
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

    @app.post("/api/v1/analyses/{analysis_id}/items/{item_id}/simulate", response_model=SimulationResponse)
    async def simulate_item(analysis_id: str, item_id: int, request: SimulationRequest):
        try:
            item = app.state.store.get_item(analysis_id, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        simulated = simulate_item_quantity(item, request.simulated_order_qty)
        return simulated

    @app.post("/api/v1/analyses/{analysis_id}/items/{item_id}/explanation", response_model=ExplanationResponse)
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
