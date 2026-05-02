from dataclasses import is_dataclass
from datetime import date, datetime, timezone
import json
import logging
from typing import Callable
import os
from queue import Empty, Queue
from threading import Thread

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import Client, ClientOptions, create_client
from dotenv import load_dotenv
from stockwise_api.api.unstructured import extract_from_unstructured_text
from pydantic import BaseModel

class UnstructuredRequest(BaseModel):
    raw_text: str

from stockwise_api.schemas import (
    AnalysisResponse,
    ChatRequest,
    ChatResponse,
    DecisionBriefResponse,
    ErrorEnvelope,
    ExplanationRequest,
    ExplanationResponse,
    ManualAnalysisRequest,
    RecordItem,
    SimulationRequest,
    SimulationResponse,
    TradeoffVerdictRequest,
    TradeoffVerdictResponse,
    RecordUpdateRequest,
    RecordsResponse,
)
from stockwise_api.services.glm import (
    build_decision_brief_context,
    build_explanation_context,
    build_inventory_chat_context,
    build_tradeoff_verdict_context,
    provider_from_env,
)
from stockwise_api.services.manual_input import (
    ManualInputValidationError,
    item_to_record_view,
    normalize_item_history,
    normalize_manual_items,
)
from stockwise_api.services.parsing import (
    ChatValidationError,
    DecisionBriefValidationError,
    build_fallback_decision_brief,
    build_fallback_chat_response,
    ExplanationValidationError,
    build_fallback_explanation,
    build_fallback_tradeoff_verdict,
    parse_chat_response,
    parse_decision_brief_response,
    parse_explanation_response,
    parse_tradeoff_verdict_response,
    TradeoffVerdictValidationError,
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


logger = logging.getLogger(__name__)


def _strip_internal_fields(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _stable_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _ai_cache_owner_key(analysis_id: str, owner_id: str | None) -> str:
    return f"{owner_id or 'anonymous'}:{analysis_id}"


def _ai_chat_cache_key(
    *,
    analysis_id: str,
    owner_id: str | None,
    message: str,
    recent_messages: list[dict],
    simulation_context: dict | None,
) -> str:
    return _stable_json(
        {
            "owner": owner_id or "anonymous",
            "analysis_id": analysis_id,
            "message": message,
            "recent_messages": recent_messages,
            "simulation_context": simulation_context,
        }
    )


def _ai_explanation_cache_key(
    *,
    analysis_id: str,
    owner_id: str | None,
    item_id: int,
    explanation_request: dict,
) -> str:
    return _stable_json(
        {
            "owner": owner_id or "anonymous",
            "analysis_id": analysis_id,
            "item_id": item_id,
            "request": explanation_request,
        }
    )


def _ai_tradeoff_verdict_cache_key(
    *,
    analysis_id: str,
    owner_id: str | None,
    item_id: int,
    simulated_order_qty: float,
) -> str:
    return _stable_json(
        {
            "owner": owner_id or "anonymous",
            "analysis_id": analysis_id,
            "item_id": item_id,
            "simulated_order_qty": simulated_order_qty,
        }
    )


def _clear_ai_cache_for_analysis(app: FastAPI, analysis_id: str, owner_id: str | None = None) -> None:
    cache = getattr(app.state, "ai_response_cache", None)
    if not cache:
        return
    owner_prefix = f"{owner_id or 'anonymous'}:{analysis_id}"
    cache.get("decision_briefs", {}).pop(owner_prefix, None)
    for bucket_name in ("chats", "explanations", "tradeoff_verdicts"):
        bucket = cache.get(bucket_name, {})
        for key in list(bucket.keys()):
            try:
                parsed = json.loads(key)
            except json.JSONDecodeError:
                continue
            if parsed.get("analysis_id") == analysis_id and parsed.get("owner") == (owner_id or "anonymous"):
                bucket.pop(key, None)


def _safe_error(
    status_code: int, error_code: str, message: str, details=None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorEnvelope(
            error_code=error_code, message=message, details=details
        ).model_dump(),
    )


def _analysis_payload(store, analysis_id: str, owner_id: str | None = None) -> dict:
    record = store.get(analysis_id, owner_id=owner_id)
    return _analysis_record_payload(analysis_id, record)


def _analysis_record_payload(analysis_id: str, record) -> dict:
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [_strip_internal_fields(item) for item in record.items],
    }


def _records_payload(store, analysis_id: str, owner_id: str | None = None) -> dict:
    record = store.get(analysis_id, owner_id=owner_id)
    return _records_payload_from_record(analysis_id, record)


def _records_payload_from_record(analysis_id: str, record) -> dict:
    return {
        "analysis_id": analysis_id,
        "dataset_summary": record.dataset_summary,
        "kpi_summary": record.kpi_summary,
        "items": [item_to_record_view(item) for item in record.items],
        "source_observations": [
            _strip_internal_fields(observation)
            for observation in getattr(record, "source_observations", [])
        ],
    }


def _record_needs_source_observation_backfill(record) -> bool:
    source_observations = getattr(record, "source_observations", []) or []
    row_count = int(record.dataset_summary.get("row_count", len(record.items)))
    return not source_observations and row_count > len(record.items)


def _backfill_source_observations_from_supabase(
    app: FastAPI,
    analysis_id: str,
    record,
    user_id: str | None,
):
    if not _record_needs_source_observation_backfill(record):
        return record

    supabase_store = app.state.supabase_store
    if supabase_store is None or not hasattr(supabase_store, "get"):
        return record

    try:
        supabase_record = _call_store_get(supabase_store, analysis_id, user_id)
    except Exception:
        return record

    source_observations = getattr(supabase_record, "source_observations", []) or []
    if not source_observations:
        return record

    record.source_observations = source_observations
    return record


def _call_store_get(store, analysis_id: str, user_id: str | None):
    if user_id is None:
        return store.get(analysis_id)
    try:
        return store.get(analysis_id, user_id)
    except TypeError:
        return store.get(analysis_id)


def _call_store_get_latest_analysis_id(store, user_id: str | None):
    if user_id is None:
        return store.get_latest_analysis_id()
    try:
        return store.get_latest_analysis_id(user_id)
    except TypeError:
        return store.get_latest_analysis_id()


def _resolve_latest_analysis_id(app: FastAPI, user_id: str | None = None) -> str:
    supabase_store = app.state.supabase_store
    if supabase_store is not None and hasattr(supabase_store, "get_latest_analysis_id"):
        try:
            analysis_id = _call_store_get_latest_analysis_id(supabase_store, user_id)
            _call_store_get(supabase_store, analysis_id, user_id)
            return analysis_id
        except Exception:
            pass
    if hasattr(app.state.store, "get_latest_analysis_id"):
        return _call_store_get_latest_analysis_id(app.state.store, user_id)
    raise KeyError("No saved analysis found.")


def _load_analysis_record(app: FastAPI, analysis_id: str, user_id: str | None = None):
    try:
        return app.state.store.get(analysis_id, owner_id=user_id)
    except KeyError:
        pass

    supabase_store = app.state.supabase_store
    if supabase_store is not None and hasattr(supabase_store, "get"):
        try:
            analysis = _call_store_get(supabase_store, analysis_id, user_id)
            app.state.store.create(
                dataset_summary=analysis.dataset_summary,
                kpi_summary=analysis.kpi_summary,
                items=analysis.items,
                analysis_id=analysis_id,
                owner_id=user_id,
                source_observations=getattr(analysis, "source_observations", []),
            )
            return analysis
        except Exception:
            pass

    raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")


def _load_analysis_item(app: FastAPI, analysis_id: str, item_id: int, user_id: str | None = None) -> dict:
    record = _load_analysis_record(app, analysis_id, user_id=user_id)
    for item in record.items:
        if int(item["item_id"]) == int(item_id):
            return item
    raise HTTPException(status_code=404, detail=f"Unknown item_id: {item_id}")


def _date_range_from_observations(items: list[dict]) -> dict:
    today = date.today().isoformat()
    dates = sorted(str(item.get("date") or today) for item in items)
    return {
        "start": dates[0] if dates else today,
        "end": dates[-1] if dates else today,
    }


def _normalize_chat_message(message: str) -> str:
    return " ".join(message.strip().split())


def _is_supported_inventory_chat_message(message: str) -> bool:
    normalized = _normalize_chat_message(message).lower()
    if not normalized:
        return False
    off_topic_markers = {
        "joke",
        "football",
        "soccer",
        "weather",
        "movie",
        "politics",
        "election",
        "recipe",
        "poem",
        "song",
    }
    return not any(marker in normalized for marker in off_topic_markers)


def _build_related_chat_items(items: list[dict], message: str) -> list[dict]:
    normalized = message.lower()
    ranked = sorted(
        items,
        key=lambda item: (
            int(item.get("recommended_action") == "RESTOCK_NOW") * 200
            + int(item.get("recommended_action") == "BUY_LESS") * 180
            + int(item.get("recommended_action") == "DELAY_PURCHASE") * 120
            + int(item.get("reorder_urgency_score", 0))
            + int(item.get("waste_risk_score", 0))
        ),
        reverse=True,
    )
    matched = [
        item
        for item in items
        if item["item_name"].lower() in normalized
        or (str(item.get("category", "")).strip() and str(item.get("category", "")).lower() in normalized)
        or (str(item.get("subcategory", "")).strip() and str(item.get("subcategory", "")).lower() in normalized)
        or (str(item.get("supplier_name", "")).strip() and str(item.get("supplier_name", "")).lower() in normalized)
    ]
    selected = (matched or ranked)[:3]
    related = []
    for item in selected:
        if item["recommended_action"] == "RESTOCK_NOW":
            reason = "Current stock does not comfortably cover near-term demand."
        elif item["recommended_action"] == "BUY_LESS":
            reason = "Waste risk is high relative to the current stock position."
        elif item["recommended_action"] == "DELAY_PURCHASE":
            reason = "Coverage is healthy enough to delay the next purchase."
        else:
            reason = "Signals are mixed, so this item should stay under review."
        related.append(
            {
                "item_id": int(item["item_id"]),
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": reason,
            }
        )
    return related


def _build_simulation_chat_context(item: dict, simulated_order_qty: float) -> dict:
    simulated = simulate_item_quantity(item, simulated_order_qty)
    return {
        "item_id": int(item["item_id"]),
        "item_name": item["item_name"],
        "simulated_order_qty": simulated["simulated_order_qty"],
        "simulated_cash_outlay": simulated["simulated_cash_outlay"],
        "simulated_coverage_days": simulated["simulated_coverage_days"],
        "simulated_risk_change": simulated["simulated_risk_change"],
        "current_recommended_action": item["recommended_action"],
        "simulated_recommended_action": simulated["recommended_action"],
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
    owner_id: str | None = None,
    source_observations: list[dict] | None = None,
) -> str:
    ranked_items = build_ranked_analysis(items)
    kpis = build_kpi_summary(ranked_items)
    if analysis_id is None:
        snapshot_id = None
        if supabase_store is not None and hasattr(supabase_store, "create_analysis_snapshot"):
            try:
                logger.warning(
                    "stockwise.analysis_snapshot.start source_type=%s owner_id=%s import_batch_id=%s row_count=%s item_count=%s source_observation_count=%s",
                    source_type or "manual",
                    owner_id,
                    import_batch_id,
                    dataset_summary.get("row_count"),
                    dataset_summary.get("item_count"),
                    len(source_observations or []),
                )
                snapshot_id = supabase_store.create_analysis_snapshot(
                    dataset_summary=dataset_summary,
                    ranked_items=ranked_items,
                    source_type=source_type or "manual",
                    import_batch_id=import_batch_id,
                    created_by=owner_id,
                    source_observations=source_observations or [],
                )
                logger.warning(
                    "stockwise.analysis_snapshot.success analysis_id=%s source_observation_count=%s",
                    snapshot_id,
                    len(source_observations or []),
                )
            except Exception as exc:
                logger.exception(
                    "stockwise.analysis_snapshot.failure source_type=%s owner_id=%s import_batch_id=%s row_count=%s item_count=%s source_observation_count=%s",
                    source_type or "manual",
                    owner_id,
                    import_batch_id,
                    dataset_summary.get("row_count"),
                    dataset_summary.get("item_count"),
                    len(source_observations or []),
                )
        else:
            logger.warning(
                "stockwise.analysis_snapshot.skipped supabase_store_ready=%s has_create_analysis_snapshot=%s",
                supabase_store is not None,
                hasattr(supabase_store, "create_analysis_snapshot"),
            )
        analysis_id = store.create(
            dataset_summary=dataset_summary,
            kpi_summary=kpis,
            items=ranked_items,
            analysis_id=snapshot_id,
            owner_id=owner_id,
            source_observations=source_observations,
        )
    else:
        store.update(
            analysis_id=analysis_id,
            dataset_summary=dataset_summary,
            kpi_summary=kpis,
            items=ranked_items,
            owner_id=owner_id,
            source_observations=source_observations,
        )
    return analysis_id


def _supabase_enabled(enable_supabase: bool | None) -> bool:
    if enable_supabase is not None:
        return enable_supabase

    flag = os.getenv("STOCKWISE_SUPABASE_ENABLED")
    if flag is not None:
        return flag.strip().lower() not in {"0", "false", "no", "off"}

    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))


def _cors_origins_from_env() -> list[str]:
    defaults = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]
    configured = [
        origin.strip().rstrip("/")
        for origin in os.getenv("STOCKWISE_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return [*defaults, *configured]


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


def _build_supabase_auth_resolver(enable_supabase: bool | None) -> Callable[[str], str | None] | None:
    if not _supabase_enabled(enable_supabase):
        return None

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        return None

    supabase_client: Client = create_client(
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        options=ClientOptions(postgrest_client_timeout=_supabase_http_timeout_seconds()),
    )

    def resolve_user_id(token: str) -> str | None:
        if not token:
            return None
        try:
            user_response = supabase_client.auth.get_user(token)
            user = getattr(user_response, "user", None)
            return getattr(user, "id", None)
        except Exception:
            return None

    return resolve_user_id


def _persist_observations(
    supabase_store,
    observations: list[dict],
    *,
    source_type: str,
    file_name: str | None = None,
    file_type: str | None = None,
    uploaded_by: str | None = None,
    created_by: str | None = None,
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
                uploaded_by=uploaded_by,
                created_by=created_by,
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


def _latest_records_by_history_identity_from_observations(observations: list[dict]) -> dict:
    latest_records: dict[str, dict] = {}
    for observation in observations:
        history_identity = observation.get("_history_identity")
        if history_identity is None:
            continue
        latest_records[history_identity] = {
            "item_id": observation.get("_supabase_item_id"),
            "record_id": observation.get("_latest_record_id"),
        }
    return latest_records


def _session_history_key(user_id: str | None) -> str:
    return user_id or "anonymous"


def _append_session_observation_history(
    app: FastAPI,
    user_id: str | None,
    observations: list[dict],
) -> list[dict]:
    history_by_owner = app.state.observation_history
    history = history_by_owner.setdefault(_session_history_key(user_id), [])
    history.extend(dict(observation) for observation in observations)
    return [dict(observation) for observation in history]


def _item_snapshot_to_source_observation(item: dict) -> dict:
    return {
        "date": item.get("date") or date.today().isoformat(),
        "item_id": item.get("item_id"),
        "item_name": item["item_name"],
        "current_stock": item["current_stock"],
        "unit": item["unit"],
        "usage_value": item.get("usage_value", item.get("daily_usage")),
        "usage_period": item.get("usage_period", "daily"),
        "lead_time_days": item.get("lead_time_days", item.get("lead_time")),
        "price_per_unit": item["price_per_unit"],
        "seasonal_factor": item["seasonal_factor"],
        "category": item.get("category"),
        "subcategory": item.get("subcategory"),
        "supplier_name": item.get("supplier_name"),
        "manual_reorder_level": item.get("manual_reorder_level", item.get("reorder_level")),
        "recent_waste_percentage": item.get("recent_waste_percentage", item.get("waste_percentage")),
    }


def _latest_cached_source_observations(app: FastAPI, user_id: str | None) -> list[dict]:
    try:
        latest_analysis_id = _resolve_latest_analysis_id(app, user_id)
        latest_record = _load_analysis_record(app, latest_analysis_id, user_id=user_id)
    except Exception:
        return []

    source_observations = getattr(latest_record, "source_observations", []) or []
    if source_observations:
        return [dict(observation) for observation in source_observations]

    return [_item_snapshot_to_source_observation(item) for item in getattr(latest_record, "items", [])]


def _cached_source_observations_for_analysis(
    app: FastAPI,
    analysis_id: str | None,
    user_id: str | None,
) -> list[dict]:
    if not analysis_id:
        return _latest_cached_source_observations(app, user_id)
    try:
        record = _load_analysis_record(app, analysis_id, user_id=user_id)
    except Exception:
        return _latest_cached_source_observations(app, user_id)

    source_observations = getattr(record, "source_observations", []) or []
    if source_observations:
        return [dict(observation) for observation in source_observations]
    return [_item_snapshot_to_source_observation(item) for item in getattr(record, "items", [])]


def _choose_complete_observation_history(
    *,
    previous_observations: list[dict],
    submitted_observations: list[dict],
    session_observations: list[dict],
    persisted_observations: list[dict] | None = None,
) -> list[dict]:
    baseline = [*previous_observations, *submitted_observations]
    if len(session_observations) > len(baseline):
        baseline = session_observations
    if persisted_observations is not None and len(persisted_observations) >= len(baseline):
        return _deduplicate_source_observations(persisted_observations)
    return _deduplicate_source_observations(baseline)


def _dedupe_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return round(float(stripped), 8)
        except ValueError:
            return stripped.lower()
    if isinstance(value, (int, float)):
        return round(float(value), 8)
    return value


def _source_observation_dedupe_key(observation: dict) -> tuple:
    return tuple(
        _dedupe_value(observation.get(field))
        for field in (
            "date",
            "item_id",
            "item_name",
            "unit",
            "category",
            "subcategory",
            "current_stock",
            "usage_value",
            "usage_period",
            "lead_time_days",
            "price_per_unit",
            "seasonal_factor",
            "supplier_name",
            "manual_reorder_level",
            "recent_waste_percentage",
            "perishability_level",
        )
    )


def _deduplicate_source_observations(observations: list[dict]) -> list[dict]:
    deduplicated = []
    seen = set()
    for observation in observations:
        key = _source_observation_dedupe_key(observation)
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(dict(observation))
    return deduplicated


def _extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _require_authenticated_user(app: FastAPI, request: Request) -> str | None:
    resolver = getattr(app.state, "auth_user_resolver", None)
    if resolver is None:
        return None
    token = _extract_bearer_token(request)
    user_id = resolver(token or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return user_id


def create_app(
    glm_provider=None,
    supabase_store=None,
    enable_supabase: bool | None = None,
    auth_user_resolver: Callable[[str], str | None] | None = None,
) -> FastAPI:
    load_dotenv()  # Load environment variables from .env file

    app = FastAPI(title="StockWise Backend", version="0.1.0")

    # Add CORS middleware (from shun branch - required for frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins_from_env(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health_check():
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "glm_mode": os.getenv("GLM_MODE", "mock"),
            "supabase_enabled": _supabase_enabled(enable_supabase),
            "supabase_store_ready": app.state.supabase_store is not None,
            "history_snapshot_table": "analysis_source_observations",
            "snapshot_write_mode": "required",
            "supabase_operation_timeout_seconds": _supabase_operation_timeout_seconds(),
            "version": "0.1.0",
            "fallback_ready": True,
        }

    app.state.store = InMemoryAnalysisStore()
    app.state.supabase_store = supabase_store if supabase_store is not None else _build_supabase_store(enable_supabase)
    app.state.glm_provider = glm_provider or provider_from_env()
    app.state.auth_user_resolver = auth_user_resolver or _build_supabase_auth_resolver(enable_supabase)
    app.state.observation_history = {}
    app.state.ai_response_cache = {
        "decision_briefs": {},
        "chats": {},
        "explanations": {},
        "tradeoff_verdicts": {},
    }

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

    @app.exception_handler(ChatValidationError)
    async def handle_chat_validation_error(_: Request, exc: ChatValidationError):
        return _safe_error(400, "chat_validation_error", str(exc))

    @app.exception_handler(DecisionBriefValidationError)
    async def handle_decision_brief_validation_error(_: Request, exc: DecisionBriefValidationError):
        return _safe_error(400, "decision_brief_validation_error", str(exc))

    @app.get("/api/v1/analyses/latest", response_model=AnalysisResponse)
    async def get_latest_analysis(request: Request):
        user_id = _require_authenticated_user(app, request)
        try:
            analysis_id = _resolve_latest_analysis_id(app, user_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="No saved analysis found.") from exc

        analysis = _load_analysis_record(app, analysis_id, user_id=user_id)
        return _analysis_record_payload(analysis_id, analysis)

    # GET endpoint added by teammate 2 (frontend needs this)
    @app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
    async def get_analysis(analysis_id: str, request: Request):
        user_id = _require_authenticated_user(app, request)
        analysis = _load_analysis_record(app, analysis_id, user_id=user_id)
        return _analysis_record_payload(analysis_id, analysis)

    @app.post("/api/v1/analyses", response_model=AnalysisResponse)
    async def create_analysis(
        request: Request,
        file: UploadFile = File(...),
        base_analysis_id: str | None = Form(None),
    ):
        user_id = _require_authenticated_user(app, request)
        raw = await file.read()
        validated_rows, _summary = validate_inventory_csv(raw)
        persistence_result = _persist_observations(
            app.state.supabase_store,
            validated_rows,
            source_type="import",
            file_name=file.filename,
            file_type="csv",
            uploaded_by=user_id,
            created_by=user_id,
        )
        previous_source_observations = _cached_source_observations_for_analysis(
            app,
            base_analysis_id,
            user_id,
        )
        session_source_observations = _append_session_observation_history(app, user_id, validated_rows)
        source_observations = _choose_complete_observation_history(
            previous_observations=previous_source_observations,
            submitted_observations=validated_rows,
            session_observations=session_source_observations,
        )
        latest_records_by_history_identity = persistence_result.get("latest_records_by_history_identity") or {}
        if (
            app.state.supabase_store is not None
            and not persistence_result.get("_timed_out")
            and hasattr(app.state.supabase_store, "list_user_observations")
        ):
            try:
                persisted_source_observations = app.state.supabase_store.list_user_observations(user_id)
                source_observations = _choose_complete_observation_history(
                    previous_observations=previous_source_observations,
                    submitted_observations=validated_rows,
                    session_observations=session_source_observations,
                    persisted_observations=persisted_source_observations,
                )
                if len(persisted_source_observations) >= len(source_observations):
                    latest_records_by_history_identity = _latest_records_by_history_identity_from_observations(
                        persisted_source_observations
                    )
            except Exception as exc:
                print(f"Failed to load user observation history from Supabase: {type(exc).__name__}: {exc}")

        normalized_items = normalize_item_history(source_observations, preserve_item_ids=True)
        normalized_items = _attach_supabase_record_links(
            normalized_items,
            {"latest_records_by_history_identity": latest_records_by_history_identity},
        )
        dataset_summary = {
            "row_count": len(source_observations),
            "item_count": len(normalized_items),
            "date_range": _date_range_from_observations(source_observations),
        }
        analysis_id = _save_analysis(
            app.state.store,
            normalized_items,
            dataset_summary,
            supabase_store=app.state.supabase_store,
            source_type="import",
            import_batch_id=persistence_result.get("import_batch_id"),
            owner_id=user_id,
            source_observations=source_observations,
        )
        return _analysis_payload(app.state.store, analysis_id, owner_id=user_id)

    @app.post("/api/v1/manual-analyses", response_model=AnalysisResponse)
    async def create_manual_analysis(request: Request, payload: ManualAnalysisRequest):
        user_id = _require_authenticated_user(app, request)
        raw_items = [item.model_dump() for item in payload.items]
        persistence_result = _persist_observations(
            app.state.supabase_store,
            raw_items,
            source_type="manual",
            uploaded_by=user_id,
            created_by=user_id,
        )
        previous_source_observations = _cached_source_observations_for_analysis(
            app,
            payload.base_analysis_id,
            user_id,
        )
        session_source_observations = _append_session_observation_history(app, user_id, raw_items)
        source_observations = _choose_complete_observation_history(
            previous_observations=previous_source_observations,
            submitted_observations=raw_items,
            session_observations=session_source_observations,
        )
        latest_records_by_history_identity = persistence_result.get("latest_records_by_history_identity") or {}
        if (
            app.state.supabase_store is not None
            and not persistence_result.get("_timed_out")
            and hasattr(app.state.supabase_store, "list_user_observations")
        ):
            try:
                persisted_source_observations = app.state.supabase_store.list_user_observations(user_id)
                source_observations = _choose_complete_observation_history(
                    previous_observations=previous_source_observations,
                    submitted_observations=raw_items,
                    session_observations=session_source_observations,
                    persisted_observations=persisted_source_observations,
                )
                if len(persisted_source_observations) >= len(source_observations):
                    latest_records_by_history_identity = _latest_records_by_history_identity_from_observations(
                        persisted_source_observations
                    )
            except Exception as exc:
                print(f"Failed to load user observation history from Supabase: {type(exc).__name__}: {exc}")

        normalized_items = normalize_item_history(source_observations, preserve_item_ids=True)
        normalized_items = _attach_supabase_record_links(
            normalized_items,
            {"latest_records_by_history_identity": latest_records_by_history_identity},
        )
        dataset_summary = {
            "row_count": len(source_observations),
            "item_count": len(normalized_items),
            "date_range": _date_range_from_observations(source_observations),
        }
        analysis_id = _save_analysis(
            app.state.store,
            normalized_items,
            dataset_summary,
            supabase_store=app.state.supabase_store,
            source_type="manual",
            import_batch_id=persistence_result.get("import_batch_id"),
            owner_id=user_id,
            source_observations=source_observations,
        )
        return _analysis_payload(app.state.store, analysis_id, owner_id=user_id)
    

    

    @app.post("/api/v1/unstructured/extract")
    async def extract_unstructured(data: dict):
        """Extract structured items from messy text"""
        print("=== RECEIVED UNSTRUCTURED REQUEST ===")
        print("Request body:", data)
        raw_text = data.get("raw_text", "")
        print(f"Raw text length: {len(raw_text)}")
        print("================================")

        if not raw_text:
            print("ERROR: No raw_text provided")
            raise HTTPException(status_code=400, detail="raw_text is required")

        extracted_items = await extract_from_unstructured_text(raw_text)
        return {
            "success": True,
            "extracted_items": extracted_items,
            "count": len(extracted_items),
            "message": f"Successfully extracted {len(extracted_items)} items."
        }
        

    @app.get("/api/v1/analyses/{analysis_id}/records", response_model=RecordsResponse)
    async def get_records(analysis_id: str, request: Request):
        user_id = _require_authenticated_user(app, request)
        analysis = _load_analysis_record(app, analysis_id, user_id=user_id)
        analysis = _backfill_source_observations_from_supabase(
            app,
            analysis_id,
            analysis,
            user_id,
        )
        return _records_payload_from_record(analysis_id, analysis)

    @app.post("/api/v1/analyses/{analysis_id}/items/{item_id}/simulate", response_model=SimulationResponse)
    async def simulate_item(analysis_id: str, item_id: int, request: Request, payload: SimulationRequest):
        user_id = _require_authenticated_user(app, request)
        item = _load_analysis_item(app, analysis_id, item_id, user_id=user_id)
        simulated = simulate_item_quantity(item, payload.simulated_order_qty)
        return simulated

    @app.post(
        "/api/v1/analyses/{analysis_id}/items/{item_id}/tradeoff-verdict",
        response_model=TradeoffVerdictResponse,
    )
    async def tradeoff_verdict(
        analysis_id: str,
        item_id: int,
        request: Request,
        payload: TradeoffVerdictRequest,
        refresh: bool = Query(False),
    ):
        user_id = _require_authenticated_user(app, request)
        item = _load_analysis_item(app, analysis_id, item_id, user_id=user_id)
        simulation = simulate_item_quantity(item, payload.simulated_order_qty)
        context = build_tradeoff_verdict_context(item, simulation)
        cache_key = _ai_tradeoff_verdict_cache_key(
            analysis_id=analysis_id,
            owner_id=user_id,
            item_id=item_id,
            simulated_order_qty=simulation["simulated_order_qty"],
        )
        verdict_cache = app.state.ai_response_cache["tradeoff_verdicts"]
        if not refresh and cache_key in verdict_cache:
            return verdict_cache[cache_key]

        provider = app.state.glm_provider
        try:
            raw = provider.generate_tradeoff_verdict(context)
            parsed = parse_tradeoff_verdict_response(raw, context)
            response = {"source": provider.source, **parsed}
            verdict_cache[cache_key] = response
            return response
        except TradeoffVerdictValidationError as exc:
            print(f"Trade-off verdict parse failed on first attempt: {type(exc).__name__}: {exc}")
            try:
                strict_context = {**context, "_strict_json": True}
                raw = provider.generate_tradeoff_verdict(strict_context)
                parsed = parse_tradeoff_verdict_response(raw, context, safety_status="retried")
                response = {"source": provider.source, **parsed}
                verdict_cache[cache_key] = response
                return response
            except Exception as retry_exc:
                print(
                    "Trade-off verdict retry failed, using fallback: "
                    f"{type(retry_exc).__name__}: {retry_exc}"
                )
                response = build_fallback_tradeoff_verdict(context)
                verdict_cache[cache_key] = response
                return response
        except Exception as exc:
            print(f"Trade-off verdict provider failed, using fallback: {type(exc).__name__}: {exc}")
            response = build_fallback_tradeoff_verdict(context)
            verdict_cache[cache_key] = response
            return response

    @app.patch(
        "/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordItem
    )
    async def update_record(
        analysis_id: str, item_id: str, request: Request, payload: RecordUpdateRequest
    ):
        user_id = _require_authenticated_user(app, request)
        try:
            # Convert item_id to int for store lookup
            record = app.state.store.get(analysis_id, owner_id=user_id)
            existing_item = app.state.store.get_item(analysis_id, int(item_id), owner_id=user_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        editable = item_to_record_view(existing_item)
        editable["date"] = existing_item["date"]
        editable["item_id"] = existing_item["item_id"]
        patch = payload.model_dump(exclude_none=True)
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
            updated_items,
            dataset_summary,
            analysis_id=analysis_id,
            owner_id=user_id,
        )
        _clear_ai_cache_for_analysis(app, analysis_id, owner_id=user_id)
        updated_item = app.state.store.get_item(analysis_id, int(item_id), owner_id=user_id)
        return item_to_record_view(updated_item)

    @app.delete(
        "/api/v1/analyses/{analysis_id}/items/{item_id}", response_model=RecordsResponse
    )
    async def delete_record(analysis_id: str, item_id: str, request: Request):
        user_id = _require_authenticated_user(app, request)
        try:
            # Convert item_id to int for store lookup
            record = app.state.store.get(analysis_id, owner_id=user_id)
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
            remaining_items,
            dataset_summary,
            analysis_id=analysis_id,
            owner_id=user_id,
        )
        _clear_ai_cache_for_analysis(app, analysis_id, owner_id=user_id)
        return _records_payload(app.state.store, analysis_id, owner_id=user_id)

    @app.post(
        "/api/v1/analyses/{analysis_id}/items/{item_id}/explanation",
        response_model=ExplanationResponse,
    )
    async def explain_item(
        analysis_id: str,
        item_id: str,
        request: Request,
        payload: ExplanationRequest,
        refresh: bool = Query(False),
    ):
        user_id = _require_authenticated_user(app, request)
        try:
            item_id_int = int(item_id)
            item = _load_analysis_item(app, analysis_id, item_id_int, user_id=user_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        explanation_request = payload.model_dump(exclude_none=True)
        cache_key = _ai_explanation_cache_key(
            analysis_id=analysis_id,
            owner_id=user_id,
            item_id=item_id_int,
            explanation_request=explanation_request,
        )
        explanation_cache = app.state.ai_response_cache["explanations"]
        if not refresh and cache_key in explanation_cache:
            return explanation_cache[cache_key]

        simulation_context = None
        if payload.simulated_order_qty is not None:
            simulation = simulate_item_quantity(item, payload.simulated_order_qty)
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
            response = {"source": provider.source, **parsed}
            explanation_cache[cache_key] = response
            return response
        except ExplanationValidationError as exc:
            print(f"Explanation parse failed on first attempt: {type(exc).__name__}: {exc}")
            try:
                strict_context = {**context, "_strict_json": True}
                raw = provider.generate_explanation(strict_context)
                parsed = parse_explanation_response(raw, context)
                response = {"source": provider.source, **parsed}
                explanation_cache[cache_key] = response
                return response
            except Exception as retry_exc:
                print(f"Explanation retry failed, using fallback: {type(retry_exc).__name__}: {retry_exc}")
                response = build_fallback_explanation(context)
                explanation_cache[cache_key] = response
                return response
        except Exception as exc:
            print(f"Explanation provider failed, using fallback: {type(exc).__name__}: {exc}")
            response = build_fallback_explanation(context)
            explanation_cache[cache_key] = response
            return response

    @app.post("/api/v1/analyses/{analysis_id}/ai-chat", response_model=ChatResponse)
    async def ai_chat(
        analysis_id: str,
        request: Request,
        payload: ChatRequest,
        refresh: bool = Query(False),
    ):
        user_id = _require_authenticated_user(app, request)
        analysis = _load_analysis_record(app, analysis_id, user_id=user_id)
        normalized_message = _normalize_chat_message(payload.message)
        recent_messages = [message.model_dump() for message in payload.recent_messages]
        simulation_payload = payload.simulation_context.model_dump() if payload.simulation_context else None
        cache_key = _ai_chat_cache_key(
            analysis_id=analysis_id,
            owner_id=user_id,
            message=normalized_message,
            recent_messages=recent_messages,
            simulation_context=simulation_payload,
        )
        chat_cache = app.state.ai_response_cache["chats"]
        if not refresh and cache_key in chat_cache:
            return chat_cache[cache_key]

        related_items = _build_related_chat_items(analysis.items, normalized_message)

        simulation_context = None
        if payload.simulation_context is not None:
            item = _load_analysis_item(
                app,
                analysis_id,
                payload.simulation_context.item_id,
                user_id=user_id,
            )
            simulation_context = _build_simulation_chat_context(
                item,
                payload.simulation_context.simulated_order_qty,
            )
            related_items = _build_related_chat_items([item], normalized_message) or related_items

        context = build_inventory_chat_context(
            message=normalized_message,
            recent_messages=recent_messages,
            dataset_summary=analysis.dataset_summary,
            kpi_summary=analysis.kpi_summary,
            items=analysis.items,
            simulation_context=simulation_context,
        )
        context["related_items"] = related_items
        context["off_topic"] = not _is_supported_inventory_chat_message(normalized_message)
        provider = app.state.glm_provider

        if context["off_topic"]:
            response = build_fallback_chat_response(context)
            chat_cache[cache_key] = response
            return response

        try:
            raw = provider.generate_inventory_chat(context)
            parsed = parse_chat_response(raw, context)
            response = {"source": provider.source, **parsed}
            chat_cache[cache_key] = response
            return response
        except ChatValidationError as exc:
            print(f"AI chat parse failed on first attempt: {type(exc).__name__}: {exc}")
            try:
                strict_context = {**context, "_strict_json": True}
                raw = provider.generate_inventory_chat(strict_context)
                parsed = parse_chat_response(raw, context)
                response = {"source": provider.source, **parsed}
                chat_cache[cache_key] = response
                return response
            except Exception as retry_exc:
                print(f"AI chat retry failed, using fallback: {type(retry_exc).__name__}: {retry_exc}")
                response = build_fallback_chat_response(context)
                chat_cache[cache_key] = response
                return response
        except Exception as exc:
            print(f"AI chat provider failed, using fallback: {type(exc).__name__}: {exc}")
            response = build_fallback_chat_response(context)
            chat_cache[cache_key] = response
            return response

    @app.get("/api/v1/analyses/{analysis_id}/decision-brief", response_model=DecisionBriefResponse)
    async def decision_brief(
        analysis_id: str,
        request: Request,
        refresh: bool = Query(False),
    ):
        user_id = _require_authenticated_user(app, request)
        analysis = _load_analysis_record(app, analysis_id, user_id=user_id)
        cache_key = _ai_cache_owner_key(analysis_id, user_id)
        decision_cache = app.state.ai_response_cache["decision_briefs"]
        if not refresh and cache_key in decision_cache:
            return decision_cache[cache_key]

        context = build_decision_brief_context(
            dataset_summary=analysis.dataset_summary,
            kpi_summary=analysis.kpi_summary,
            items=analysis.items,
        )
        provider = app.state.glm_provider

        try:
            raw = provider.generate_decision_brief(context)
            parsed = parse_decision_brief_response(raw, context)
            response = {"source": provider.source, **parsed}
            decision_cache[cache_key] = response
            return response
        except DecisionBriefValidationError as exc:
            print(f"Decision brief parse failed on first attempt: {type(exc).__name__}: {exc}")
            try:
                strict_context = {**context, "_strict_json": True}
                raw = provider.generate_decision_brief(strict_context)
                parsed = parse_decision_brief_response(raw, context, safety_status="retried")
                response = {"source": provider.source, **parsed}
                decision_cache[cache_key] = response
                return response
            except Exception as retry_exc:
                print(
                    "Decision brief retry failed, using fallback: "
                    f"{type(retry_exc).__name__}: {retry_exc}"
                )
                response = build_fallback_decision_brief(context)
                decision_cache[cache_key] = response
                return response
        except Exception as exc:
            print(f"Decision brief provider failed, using fallback: {type(exc).__name__}: {exc}")
            response = build_fallback_decision_brief(context)
            decision_cache[cache_key] = response
            return response

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
