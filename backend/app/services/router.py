"""Agent / router: classifies task type from (query, input configuration).

This is a REAL, working rule-based classifier — not a placeholder that
pretends to be an LLM. It is intentionally simple and auditable. The target
architecture calls for an LLM-based orchestrator (e.g. via LangGraph); this
keyword+config classifier is the documented Phase-A stand-in so the rest of
the pipeline (validation → routing → tool registry → execution trace) is
real and testable end-to-end before an LLM router is wired in.

Upgrade path (documented in README): replace `classify_task()` with a call
to an LLM given the query + input configuration + a JSON schema for
TaskType, keeping the same function signature so nothing downstream changes.
"""
from __future__ import annotations

from app.models.schemas import InputConfiguration, TaskType

_CHANGE_KEYWORDS = {"change", "changed", "increase", "decrease", "before and after", "between"}
_GROUNDING_KEYWORDS = {"highlight", "locate", "where is", "point to", "show me the"}
_CAPTION_KEYWORDS = {"describe", "caption", "summarize this image", "what is visible"}


def classify_task(query: str, input_configuration: InputConfiguration) -> tuple[TaskType, list[str]]:
    """Returns (task, reasoning_notes). Pure function, fully testable."""
    q = query.lower()
    notes: list[str] = []

    if input_configuration == InputConfiguration.INCOMPATIBLE:
        notes.append("Input configuration is incompatible with any supported task.")
        return TaskType.UNSUPPORTED, notes

    if input_configuration == InputConfiguration.BITEMPORAL_PAIR:
        if any(k in q for k in _CHANGE_KEYWORDS):
            notes.append("Bi-temporal pair + change-related keywords -> change_vqa.")
            return TaskType.CHANGE_VQA, notes
        notes.append(
            "Bi-temporal pair supplied but query has no change-related "
            "keywords -> defaulting to change_detection so the user gets a "
            "change map even without an explicit 'what changed' phrasing."
        )
        return TaskType.CHANGE_DETECTION, notes

    if input_configuration == InputConfiguration.CROSS_MODAL_PAIR:
        notes.append("Optical + SAR pair supplied -> optical_sar_analysis.")
        return TaskType.OPTICAL_SAR_ANALYSIS, notes

    # Single image
    if any(k in q for k in _GROUNDING_KEYWORDS):
        notes.append("Single image + localization keywords -> grounding.")
        return TaskType.GROUNDING, notes
    if any(k in q for k in _CAPTION_KEYWORDS):
        notes.append("Single image + description keywords -> captioning.")
        return TaskType.CAPTIONING, notes

    notes.append("Single image, no special keywords matched -> default to vqa.")
    return TaskType.VQA, notes


def determine_input_configuration(num_images: int, modalities: list[str]) -> InputConfiguration:
    """Determine configuration from image count + user-declared modalities.

    Real modality identity (optical vs SAR) cannot be inferred from pixels
    alone in this scaffold (see services/validation.py) — the caller must
    supply user-declared or metadata-derived modalities here rather than a
    guess, so this function never fabricates a configuration it can't verify.
    """
    if num_images == 1:
        return InputConfiguration.SINGLE_IMAGE
    if num_images == 2:
        if modalities.count("optical") == 1 and modalities.count("sar") == 1:
            return InputConfiguration.CROSS_MODAL_PAIR
        if len(set(modalities)) == 1 and modalities[0] != "unknown":
            return InputConfiguration.BITEMPORAL_PAIR
        return InputConfiguration.INCOMPATIBLE
    return InputConfiguration.INCOMPATIBLE
