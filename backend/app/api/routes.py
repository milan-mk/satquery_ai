from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import (
    Evidence,
    ExecutionStep,
    InputConfiguration,
    Modality,
    QueryRequest,
    QueryResponse,
    UploadedImageMeta,
    UploadResponse,
)
from app.services.router import classify_task, determine_input_configuration
from app.services.validation import UnsupportedFormatError, validate_image_bytes
from app.tools.registry import TOOL_REGISTRY, ModelNotIntegratedError

router = APIRouter()

STORAGE_DIR = Path(__file__).resolve().parents[2] / "storage" / "uploads"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory store for this scaffold. README documents the PostgreSQL swap-in.
_FILES: dict[str, UploadedImageMeta] = {}
_FILE_PATHS: dict[str, str] = {}  # file_id -> real path on disk, needed by tools that call an external model
_EXECUTIONS: dict[str, QueryResponse] = {}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.post("/upload", response_model=UploadResponse)
async def upload(files: list[UploadFile] = File(...)) -> UploadResponse:
    if not files:
        raise HTTPException(400, "No files supplied.")
    if len(files) > 2:
        raise HTTPException(400, "At most 2 images are supported (single image or a pair).")

    metas: list[UploadedImageMeta] = []
    notes: list[str] = []

    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(413, f"'{f.filename}' exceeds the {MAX_FILE_SIZE_BYTES} byte limit.")
        if not data:
            raise HTTPException(400, f"'{f.filename}' is empty.")

        try:
            validated = validate_image_bytes(data, f.filename or "upload")
        except UnsupportedFormatError as exc:
            raise HTTPException(422, str(exc)) from exc

        file_id = str(uuid.uuid4())
        # sanitize filename before writing to disk
        safe_name = Path(f.filename or "upload").name.replace("..", "_")
        dest = STORAGE_DIR / f"{file_id}_{safe_name}"
        dest.write_bytes(data)

        meta = UploadedImageMeta(
            file_id=file_id,
            filename=safe_name,
            content_type=f.content_type or "application/octet-stream",
            size_bytes=len(data),
            modality=Modality.UNKNOWN,
            format=validated.format,
            width=validated.width,
            height=validated.height,
            has_geo_metadata=validated.has_geo_metadata,
            uploaded_at=datetime.now(timezone.utc),
        )
        _FILES[file_id] = meta
        _FILE_PATHS[file_id] = str(dest)
        metas.append(meta)
        notes.extend(f"[{safe_name}] {n}" for n in validated.notes)

    # Without confirmed modality we can't yet know cross-modal vs bi-temporal;
    # report single_image for 1 file, otherwise ask the client to declare
    # modality via the query step (see README: modality confirmation flow).
    config = InputConfiguration.SINGLE_IMAGE if len(metas) == 1 else InputConfiguration.INCOMPATIBLE
    if len(metas) == 2:
        notes.append(
            "Two images uploaded but modality is not yet confirmed — pass "
            "modality hints in your query, e.g. 'these are optical and SAR "
            "images of the same area' or 'these are before/after images'."
        )

    return UploadResponse(files=metas, input_configuration=config, validation_notes=notes)


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    trace: list[ExecutionStep] = []

    missing = [fid for fid in req.file_ids if fid not in _FILES]
    if missing:
        raise HTTPException(400, f"Unknown file_ids: {missing}")

    if not (1 <= len(req.file_ids) <= 2):
        raise HTTPException(400, "Provide 1 image (single) or 2 images (pair).")

    trace.append(ExecutionStep(step="input_validation", status="success"))

    q_lower = req.query.lower()
    declared_modalities: list[str] = []
    if len(req.file_ids) == 2:
        if "optical" in q_lower and "sar" in q_lower:
            declared_modalities = ["optical", "sar"]
        elif any(w in q_lower for w in ("before", "after", "between these", "changed")):
            declared_modalities = ["same", "same"]  # same-modality bi-temporal
        else:
            trace.append(ExecutionStep(
                step="modality_confirmation",
                status="failed",
                detail=(
                    "Two images given but modality/relationship couldn't be "
                    "determined from the query. State e.g. 'optical and SAR "
                    "images' or 'before and after images' in your query."
                ),
            ))
            return QueryResponse(task="unsupported", status="blocked", execution_trace=trace)  # type: ignore[arg-type]

    input_config = determine_input_configuration(len(req.file_ids), declared_modalities or ["optical"])
    task, reasoning = classify_task(req.query, input_config)
    trace.append(ExecutionStep(step="query_classification", status="success", detail="; ".join(reasoning)))

    if task == "unsupported":
        trace.append(ExecutionStep(step="model_selection", status="skipped", detail="No compatible task."))
        return QueryResponse(task=task, status="blocked", execution_trace=trace)

    tool = TOOL_REGISTRY.get(task.value)
    trace.append(ExecutionStep(step="model_selection", status="success", model=tool.required_model if tool else None))

    try:
        # Single-image tools (vqa, captioning, grounding) need the real file
        # path, not just the id — tools that need more than one image (change
        # detection, optical+sar) would extend this call with the second path.
        image_path = _FILE_PATHS[req.file_ids[0]]
        result = tool.run(image_path=image_path, query=req.query) if tool else None
    except ModelNotIntegratedError as exc:
        trace.append(ExecutionStep(step="inference", status="not_implemented", detail=str(exc)))
        response = QueryResponse(
            task=task,
            answer=None,
            confidence=None,
            evidence=[],
            execution_trace=trace,
            status="blocked",
        )
        _EXECUTIONS[str(uuid.uuid4())] = response
        return response

    trace.append(ExecutionStep(step="inference", status="success"))
    response = QueryResponse(
        task=task,
        answer=result.get("answer") if result else None,
        confidence=result.get("confidence") if result else None,
        execution_trace=trace,
        status="completed",
    )
    _EXECUTIONS[str(uuid.uuid4())] = response
    return response
