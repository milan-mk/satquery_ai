"""Pydantic request/response models for SatQuery AI."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Modality(str, Enum):
    OPTICAL = "optical"
    SAR = "sar"
    UNKNOWN = "unknown"


class InputConfiguration(str, Enum):
    SINGLE_IMAGE = "single_image"
    CROSS_MODAL_PAIR = "cross_modal_pair"       # optical + SAR, same time
    BITEMPORAL_PAIR = "bitemporal_pair"         # same modality, two times
    INCOMPATIBLE = "incompatible"


class TaskType(str, Enum):
    VQA = "vqa"
    CAPTIONING = "captioning"
    GROUNDING = "grounding"
    CHANGE_DETECTION = "change_detection"
    CHANGE_VQA = "change_vqa"
    OPTICAL_SAR_ANALYSIS = "optical_sar_analysis"
    UNSUPPORTED = "unsupported"


class UploadedImageMeta(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size_bytes: int
    modality: Modality
    format: str
    width: Optional[int] = None
    height: Optional[int] = None
    has_geo_metadata: bool = False
    uploaded_at: datetime


class UploadResponse(BaseModel):
    files: list[UploadedImageMeta]
    input_configuration: InputConfiguration
    validation_notes: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    file_ids: list[str]
    query: str


class ExecutionStep(BaseModel):
    step: str
    status: str  # "success" | "failed" | "skipped" | "not_implemented"
    detail: Optional[str] = None
    model: Optional[str] = None


class Evidence(BaseModel):
    kind: str  # "bounding_box" | "mask" | "change_map" | "overlay"
    file_id: Optional[str] = None
    note: Optional[str] = None


class QueryResponse(BaseModel):
    task: TaskType
    answer: Optional[str] = None
    confidence: Optional[float] = None
    evidence: list[Evidence] = Field(default_factory=list)
    execution_trace: list[ExecutionStep]
    status: str  # "completed" | "blocked" | "error"
