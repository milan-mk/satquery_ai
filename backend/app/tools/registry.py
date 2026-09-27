"""Modular specialist-tool registry.

Per the project's "never fake success" rule, every tool in this registry is a
real, isolated adapter. Where a tool has no real model wired up yet (because
this environment has no GPU and no access to model hosts like
huggingface.co), `run()` raises `ModelNotIntegratedError` with a clear
explanation rather than returning invented output. See README for the exact
integration steps to wire in GeoChat / RemoteCLIP / BIT once you have a
GPU-enabled environment with model access.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ModelNotIntegratedError(RuntimeError):
    """Raised when a tool is selected but has no real backing model in this
    environment. Never caught silently — the API surfaces this as a 'blocked'
    status, never as a fabricated answer."""


class SpecialistTool(ABC):
    name: str
    required_model: str

    @abstractmethod
    def run(self, **kwargs: Any) -> dict:
        ...


class VQATool(SpecialistTool):
    name = "vqa"
    required_model = "GeoChat-7B"

    # --- Real integration, verified against an actual GeoChat run ---
    # This calls GeoChat as a SUBPROCESS in its own isolated conda
    # environment (Python 3.10), rather than importing it directly into
    # this FastAPI process. This is deliberate, not a workaround to remove
    # later: GeoChat's pinned 2023-era dependencies (transformers==4.31.0,
    # peft==0.4.0, etc.) would conflict with this backend's own modern
    # dependencies (Pydantic v2, etc.) if installed into the same
    # environment. Subprocess isolation sidesteps that entirely.
    #
    # REQUIRED PATHS — edit these three to match your actual GPU machine:
    CONDA_PYTHON = "/kaggle/working/miniconda/envs/geochat/bin/python"  # or /kaggle/working/miniconda/...
    INFERENCE_SCRIPT = "/kaggle/working/GeoChat/run_inference.py"        # or /kaggle/working/GeoChat/...
    MODEL_PATH = "/kaggle/working/geochat-7b"                            # or /kaggle/working/geochat-7b

    def run(self, image_path: str, query: str, **kwargs: Any) -> dict:
        import json
        import subprocess
        import tempfile
        import os

        if not os.path.exists(self.CONDA_PYTHON):
            raise ModelNotIntegratedError(
                f"'{self.name}' is configured but the conda environment at "
                f"{self.CONDA_PYTHON} doesn't exist on this machine. This "
                "backend must run on the same GPU machine (Kaggle/Colab/etc.) "
                "where GeoChat was set up — see README 'Running with a real "
                "GPU backend'. Update CONDA_PYTHON/INFERENCE_SCRIPT/MODEL_PATH "
                "in this file to match your actual paths."
            )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_json_path = tmp.name

        try:
            result = subprocess.run(
                [
                    self.CONDA_PYTHON, "-u", self.INFERENCE_SCRIPT,
                    "--model-path", self.MODEL_PATH,
                    "--image-file", image_path,
                    "--question", query,
                    "--max-new-tokens", "256",
                    "--output-json", output_json_path,
                ],
                capture_output=True,
                text=True,
                timeout=300,  # real 7B inference can be slow; adjust once you know your hardware's typical time
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelNotIntegratedError(f"GeoChat inference timed out after 300s: {exc}") from exc

        if result.returncode != 0:
            # Never fabricate an answer on failure — surface the real stderr.
            raise ModelNotIntegratedError(
                f"GeoChat subprocess failed (exit {result.returncode}). "
                f"stderr tail: {result.stderr[-1500:]}"
            )

        if not os.path.exists(output_json_path) or os.path.getsize(output_json_path) == 0:
            raise ModelNotIntegratedError(
                "GeoChat subprocess exited successfully but wrote no output JSON — "
                f"check run_inference.py's --output-json handling. stdout tail: {result.stdout[-1000:]}"
            )

        with open(output_json_path) as f:
            parsed = json.load(f)
        os.remove(output_json_path)

        return {"answer": parsed["answer"], "confidence": None}  # GeoChat has no native confidence score — never invent one


class CaptioningTool(SpecialistTool):
    name = "captioning"
    required_model = "GeoChat or BLIP-family model fine-tuned on remote sensing"

    def run(self, **kwargs: Any) -> dict:
        raise ModelNotIntegratedError(
            f"'{self.name}' requires {self.required_model} — not integrated yet."
        )


class GroundingTool(SpecialistTool):
    name = "grounding"
    required_model = "Remote-sensing grounding model (e.g. GeoChat-grounding)"

    def run(self, **kwargs: Any) -> dict:
        raise ModelNotIntegratedError(
            f"'{self.name}' requires {self.required_model} — not integrated yet."
        )


class ChangeDetectionTool(SpecialistTool):
    name = "change_detection"
    required_model = "BIT (Bitemporal Image Transformer) or equivalent"

    def run(self, **kwargs: Any) -> dict:
        raise ModelNotIntegratedError(
            f"'{self.name}' requires {self.required_model} — not integrated yet."
        )


class OpticalSARTool(SpecialistTool):
    name = "optical_sar_analysis"
    required_model = "Modality-specific encoders + consistency-scoring layer"

    def run(self, **kwargs: Any) -> dict:
        raise ModelNotIntegratedError(
            f"'{self.name}' requires {self.required_model} — not integrated yet."
        )


TOOL_REGISTRY: dict[str, SpecialistTool] = {
    "vqa": VQATool(),
    "captioning": CaptioningTool(),
    "grounding": GroundingTool(),
    "change_detection": ChangeDetectionTool(),
    "optical_sar_analysis": OpticalSARTool(),
}
