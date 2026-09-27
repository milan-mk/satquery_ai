"""Input validation for uploaded imagery.

This module performs REAL validation (file format, dimensions, basic modality
heuristic) using Pillow. It does NOT fabricate geo-metadata or sensor
identity it cannot actually determine.

Known limitation (documented, not hidden): true GeoTIFF metadata parsing
(CRS, band count semantics, SAR polarization tags) requires rasterio/GDAL,
which is not installed in this scaffold to keep the environment lean. See
README "Known Limitations" for the exact follow-up steps.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

SUPPORTED_FORMATS = {"TIFF", "PNG", "JPEG"}


@dataclass
class ValidatedImage:
    format: str
    width: int
    height: int
    has_geo_metadata: bool
    modality_guess: str  # "optical" | "sar" | "unknown"
    notes: list[str]


class UnsupportedFormatError(ValueError):
    pass


def validate_image_bytes(data: bytes, filename: str) -> ValidatedImage:
    """Validate an uploaded image's format and extract what we can determine
    honestly from pixel data alone.

    SAR vs optical cannot be reliably determined from a bare PNG/JPEG/TIFF
    without band-count/metadata inspection (rasterio) or the user telling us.
    We report "unknown" rather than guessing, per the no-fabrication rule.
    """
    notes: list[str] = []
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        # re-open: verify() invalidates the file handle for further use
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or "").upper()
    except Exception as exc:  # noqa: BLE001 - surfaced to caller as a clear error
        raise UnsupportedFormatError(f"Could not decode '{filename}' as an image: {exc}") from exc

    if fmt not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Format '{fmt}' from '{filename}' is not supported. "
            f"Supported: {sorted(SUPPORTED_FORMATS)}."
        )

    width, height = img.size

    has_geo_metadata = False
    if fmt == "TIFF":
        # Pillow exposes some TIFF tags; real CRS/geotransform requires GDAL.
        tag_keys = set(getattr(img, "tag_v2", {}).keys()) if hasattr(img, "tag_v2") else set()
        geo_tag_ids = {33550, 33922, 34264, 34735, 34736, 34737}  # GeoTIFF tags
        has_geo_metadata = bool(tag_keys & geo_tag_ids)
        if not has_geo_metadata:
            notes.append(
                "TIFF has no standard GeoTIFF georeferencing tags detected "
                "(or Pillow could not read them) — treating as non-georeferenced."
            )
    else:
        notes.append(f"{fmt} accepted for benchmark/demo use only, per input-scope spec.")

    # Honest modality heuristic: single-band imagery often indicates SAR
    # amplitude data, but this is a weak signal, not a determination.
    band_count = len(img.getbands())
    if band_count == 1:
        modality_guess = "unknown"
        notes.append(
            "Single-band image detected — could be SAR amplitude or a "
            "single optical band. Modality must be confirmed by the user "
            "or by real GDAL/metadata inspection, not guessed."
        )
    else:
        modality_guess = "unknown"
        notes.append(
            f"{band_count}-band image — modality not determinable from pixel "
            f"data alone in this scaffold; user-provided modality is required."
        )

    return ValidatedImage(
        format=fmt,
        width=width,
        height=height,
        has_geo_metadata=has_geo_metadata,
        modality_guess=modality_guess,
        notes=notes,
    )
