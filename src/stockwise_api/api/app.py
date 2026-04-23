from dataclasses import asdict, is_dataclass
from datetime import date
import os
from queue import Empty, Queue
from threading import Thread

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import Client, ClientOptions, create_client
from dotenv import load_dotenv

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
from stockwise_api.services.parsing import (
    ExplanationValidationError,
    build_fallback_explanation,
    parse_explanation_response,
)
from stockwise_api.services.recommendations import (
    build_kpi_summary,
    build_ranked_analysis,
)
from stockwise_api.services.simulation import simulate_item_quantity
from stockwise_api.services.validation import (
    ValidationError,
    validate_inventory_csv,
)
from stockwise_api.store import InMemoryAnalysisStore, SupabaseAnalysisStore


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
    return _analysis_record_payload(analysis_id, record)


def _analysis_record_payload(analysis_id: str, record) -> dict:
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [_strip_internal_fields(item) for item in record.items],
    }


def _records_payload(store, analysis_id: str) -> dict:
    record = store.get(analysis_id)
    return _records_payload_from_record(analysis_id, record)


def _records_payload_from_record(analysis_id: str, record) -> dict:
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [item_to_record_view(item) for item in record.items],
    }


def _load_analysis_record(app: FastAPI, analysis_id: str):
    try:
        return app.state.store.get(analysis_id)
    except KeyError:
        pass

    supabase_store = app.state.supabase_store
    if supabase_store is not None and hasattr(supabase_store, "get"):
        try:
            analysis = supabase_store.get(analysis_id)
            app.state.store.create(
                dataset_summary=analysis.dataset_summary,
                kpi_summary=analysis.kpi_summary,
                items=analysis.items,
                analysis_id=analysis_id,
            )
            return analysis
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")


def _load_analysis_item(app: FastAPI, analysis_id: str, item_id: int) -> dict:
    record = _load_analysis_record(app, analysis_id)
    for item in record.items:
        if int(item["item_id"]) == int(item_id):
            return item
    raise HTTPException(status_code=404, detail=f"Unknown item_id: {item_id}")


def _date_range_from_manual_items(items: list[dict]) -> dict:
    today = date.today().isoformat()
    dates = sorted(str(item.get("date") or today) for item in items)
    return {
        "start": dates[0] if dates else today,
        "end": dates[-1] if dates else today,
    }


def _save_analysis(
    store,
    items: list[dict],
    dataset_summary: dict,
    analysis_id: str | None = None,
    *,
    supabase_store=None,
    source_type: str | None = None,
    import_batch_id: str | None = None,
) -> str:
    ranked_items = build_ranked_analysis(items)
    kpis = build_kpi_summary(ranked_items)
    if analysis_id is None:
        snapshot_id = None
        if supabase_store is not None and hasattr(supabase_store, "create_analysis_snapshot"):
            try:
                snapshot_id = _run_optional_supabase_operation(
                    "create-analysis-snapshot",
                    lambda: supabase_store.create_analysis_snapshot(
                        dataset_summary=dataset_summary,
                        ranked_items=ranked_items,
                        source_type=source_type or "manual",
                        import_batch_id=import_batch_id,
                    ),
                    lambda: None,
                )
            except Exception as exc:
                print(f"Failed to persist analysis snapshot to Supabase: {type(exc).__name__}: {exc}")
        analysis_id = store.create(
            dataset_summary=dataset_summary,
            kpi_summary=kpis,
            items=ranked_items,
            analysis_id=snapshot_id,
        )
    else:
        store.update(analysis_id=analysis_id, dataset_summary=dataset_summary, kpi_summary=kpis, items=ranked_items)
    return analysis_id


def _supabase_enabled(enable_supabase: bool | None) -> bool:
    if enable_supabase is not None:
        return enable_supabase

    flag = os.getenv("STOCKWISE_SUPABASE_ENABLED")
    if flag is not None:
        return flag.strip().lower() not in {"0", "false", "no", "off"}

    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        print(f"Ignoring invalid {name} value: {raw_value!r}")
        return default


def _supabase_operation_timeout_seconds() -> float:
    return max(_env_float("STOCKWISE_SUPABASE_OPERATION_TIMEOUT_SECONDS", 5.0), 0.0)


def _supabase_http_timeout_seconds() -> float:
    return max(_env_float("STOCKWISE_SUPABASE_HTTP_TIMEOUT_SECONDS", 5.0), 0.1)


def _run_optional_supabase_operation(operation_name: str, operation, fallback):
    timeout_seconds = _supabase_operation_timeout_seconds()
    if timeout_seconds <= 0:
        return operation()

    result_queue: Queue = Queue(maxsize=1)

    def run_operation() -> None:
        try:
            result_queue.put((True, operation()))
        except Exception as exc:
            result_queue.put((False, exc))

    Thread(
        target=run_operation,
        name=f"stockwise-supabase-{operation_name}",
        daemon=True,
    ).start()

    try:
        success, result = result_queue.get(timeout=timeout_seconds)
    except Empty:
        print(
            f"Timed out waiting {timeout_seconds:g}s for Supabase {operation_name}; "
            "continuing without blocking the upload response."
        )
        fallback_result = fallback()
        if isinstance(fallback_result, dict):
            fallback_result["_timed_out"] = True
        return fallback_result

    if success:
        return result
    raise result


def _build_supabase_store(enable_supabase: bool | None):
    if not _supabase_enabled(enable_supabase):
        return None

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print("Supabase persistence is enabled but SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing.")
        return None

    supabase_client: Client = create_client(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        options=ClientOptions(postgrest_client_timeout=_supabase_http_timeout_seconds()),
    )
    return SupabaseAnalysisStore(supabase_client)


def _persist_observations(
    supabase_store,
    observations: list[dict],
    *,
    source_type: str,
    file_name: str | None = None,
    file_type: str | None = None,
) -> dict:
    if supabase_store is None:
        return {"import_batch_id": None, "successful_rows": 0, "failed_rows": 0}

    try:
        fallback_result = {"import_batch_id": None, "successful_rows": 0, "failed_rows": len(observations)}
        result = _run_optional_supabase_operation(
            "persist-observations",
            lambda: supabase_store.persist_observations(
                observations,
                source_type=source_type,
                file_name=file_name,
                file_type=file_type,
            ),
            lambda: fallback_result.copy(),
        )
        return result or {"import_batch_id": None, "successful_rows": len(observations), "failed_rows": 0}
    except Exception as exc:
        print(f"Failed to persist observations to Supabase: {type(exc).__name__}: {exc}")
        return {"import_batch_id": None, "successful_rows": 0, "failed_rows": len(observations)}


def _attach_supabase_record_links(items: list[dict], persistence_result: dict) -> list[dict]:
    latest_records = persistence_result.get("latest_records_by_history_identity") or {}
    if not latest_records:
        return items

    linked_items = []
    for item in items:
        linked_item = dict(item)
        latest_record = latest_records.get(item.get("_history_identity"))
        if latest_record:
            linked_item["_supabase_item_id"] = latest_record.get("item_id")
            linked_item["_latest_record_id"] = latest_record.get("record_id")
        linked_items.append(linked_item)
    return linked_items


def create_app(glm_provider=None, supabase_store=None, enable_supabase: bool | None = None) -> FastAPI:
    load_dotenv()  # Load environment variables from .env file

    app = FastAPI(title="StockWise Backend", version="0.1.0")

    # Add CORS middleware (from shun branch - required for frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
        # allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.store = InMemoryAnalysisStore()
    app.state.supabase_store = supabase_store if supabase_store is not None else _build_supabase_store(enable_supabase)
    app.state.glm_provider = glm_provider or provider_from_env()

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError):
        return _safe_error(400, "validation_error", str(exc))

    @app.exception_handler(ManualInputValidationError)
    async def handle_manual_input_validation_error(
        _: Request, exc: ManualInputValidationError
    ):
        return _safe_error(400, "manual_input_validation_error", str(exc))

    @app.exception_handler(ExplanationValidationError)
    async def handle_explanation_validation_error(
        _: Request, exc: ExplanationValidationError
    ):
        return _safe_error(400, "explanation_validation_error", str(exc))

    @app.get("/api/v1/analyses/latest", response_model=AnalysisResponse)
    async def get_latest_analysis():
        supabase_store = app.state.supabase_store
        if supabase_store is None or not hasattr(supabase_store, "get_latest_analysis_id"):
            raise HTTPException(status_code=404, detail="No saved analysis found.")

        try:
            analysis_id = supabase_store.get_latest_analysis_id()
        except Exception as exc:
            raise HTTPException(status_code=404, detail="No saved analysis found.") from exc

        analysis = _load_analysis_record(app, analysis_id)
        return _analysis_record_payload(analysis_id, analysis)

    # GET endpoint added by teammate 2 (frontend needs this)
    @app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
    async def get_analysis(analysis_id: str):
        analysis = _load_analysis_record(app, analysis_id)
        return _analysis_record_payload(analysis_id, analysis)

    @app.post("/api/v1/analyses", response_model=AnalysisResponse)
    async def create_analysis(file: UploadFile = File(...)):
        raw = await file.read()
        validated_rows, summary = validate_inventory_csv(raw)
        persistence_result = _persist_observations(
            app.state.supabase_store,
            validated_rows,
            source_type="import",
            file_name=file.filename,
            file_type="csv",
        )
        normalized_items = normalize_item_history(validated_rows, preserve_item_ids=True)
        normalized_items = _attach_supabase_record_links(normalized_items, persistence_result)
        dataset_summary = asdict(summary)
        dataset_summary["item_count"] = len(normalized_items)
        supabase_store_for_snapshot = None if persistence_result.get("_timed_out") else app.state.supabase_store
        analysis_id = _save_analysis(
            app.state.store,
            normalized_items,
            dataset_summary,
            supabase_store=supabase_store_for_snapshot,
            source_type="import",
            import_batch_id=persistence_result.get("import_batch_id"),
        )
        return _analysis_payload(app.state.store, analysis_id)

    @app.post("/api/v1/manual-analyses", response_model=AnalysisResponse)
    async def create_manual_analysis(request: ManualAnalysisRequest):
        raw_items = [item.model_dump() for item in request.items]
        persistence_result = _persist_observations(
            app.state.supabase_store,
            raw_items,
            source_type="manual",
        )
        normalized_items = normalize_item_history(raw_items, preserve_item_ids=True)
        normalized_items = _attach_supabase_record_links(normalized_items, persistence_result)
        dataset_summary = {
            "row_count": len(raw_items),
            "item_count": len(normalized_items),
            "date_range": _date_range_from_manual_items(raw_items),
        }
        supabase_store_for_snapshot = None if persistence_result.get("_timed_out") else app.state.supabase_store
        analysis_id = _save_analysis(
            app.state.store,
            normalized_items,
            dataset_summary,
            supabase_store=supabase_store_for_snapshot,
            source_type="manual",
            import_batch_id=persistence_result.get("import_batch_id"),
        )
        return _analysis_payload(app.state.store, analysis_id)

    @app.get("/api/v1/analyses/{analysis_id}/records", response_model=RecordsResponse)
    async def get_records(analysis_id: str):
        analysis = _load_analysis_record(app, analysis_id)
        return _records_payload_from_record(analysis_id, analysis)

    @app.post("/api/v1/analyses/{analysis_id}/items/{item_id}/simulate", response_model=SimulationResponse)
    async def simulate_item(analysis_id: str, item_id: int, request: SimulationRequest):
        item = _load_analysis_item(app, analysis_id, item_id)
        simulated = simulate_item_quantity(item, request.simulated_order_qty)
        return simulated

    @app.patch(
        "/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordItem
    )
    async def update_record(
        analysis_id: str, item_id: str, request: RecordUpdateRequest
    ):
        try:
            # Convert item_id to int for store lookup
            record = app.state.store.get(analysis_id)
            existing_item = app.state.store.get_item(analysis_id, int(item_id))
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        editable = item_to_record_view(existing_item)
        editable["date"] = existing_item["date"]
        editable["item_id"] = existing_item["item_id"]
        patch = request.model_dump(exclude_none=True)
        editable.update(patch)
        normalized_item = normalize_manual_items([editable], preserve_item_ids=True)[0]
        normalized_item["_observation_count"] = int(
            existing_item.get("_observation_count", 1)
        )
        updated_items = [
            normalized_item if int(item["item_id"]) == int(item_id) else item
            for item in record.items
        ]
        dataset_summary = {
            **record.dataset_summary,
            "item_count": len(updated_items),
        }
        _save_analysis(
            app.state.store,
            app.state.supabase_store,
            updated_items,
            dataset_summary,
            analysis_id=analysis_id,
        )
        updated_item = app.state.store.get_item(analysis_id, int(item_id))
        return item_to_record_view(updated_item)

    @app.delete(
        "/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordsResponse
    )
    async def delete_record(analysis_id: str, item_id: str):
        try:
            # Convert item_id to int for store lookup
            record = app.state.store.get(analysis_id)
            item_id_int = int(item_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        remaining_items = [
            item for item in record.items if int(item["item_id"]) != item_id_int
        ]
        if len(remaining_items) == len(record.items):
            raise HTTPException(status_code=404, detail=f"Unknown item_id: {item_id}")
        if not remaining_items:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last remaining item in the analysis.",
            )
        removed_item = next(
            item for item in record.items if int(item["item_id"]) == item_id_int
        )
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
        _save_analysis(
            app.state.store,
            app.state.supabase_store,
            remaining_items,
            dataset_summary,
            analysis_id=analysis_id,
        )
        return _records_payload(app.state.store, analysis_id)

    @app.post(
        "/api/v1/analyses/{analysis_id}/items/{item_id}/explanation",
        response_model=ExplanationResponse,
    )
    async def explain_item(analysis_id: str, item_id: str, request: ExplanationRequest):
        try:
            # Convert item_id to int for store lookup
            item_id_int = int(item_id)
            # Try to get from Supabase store first, fall back to in-memory store
            item = app.state.supabase_store.get_item(analysis_id, item_id_int)
        except (KeyError, NotImplementedError, ValueError):
            try:
                item_id_int = int(item_id)
                item = app.state.store.get_item(analysis_id, item_id_int)
            except (KeyError, ValueError) as exc:
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

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(_: Request, exc: Exception):
        print(f"Unhandled exception: {type(exc).__name__}: {exc}")
        return _safe_error(500, "internal_error", str(exc))

    return app
