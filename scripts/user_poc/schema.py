"""Schema helpers for canonical User_Face_Features rows.

This module intentionally mirrors the real User_Face_Features schema 1:1.
PoC diagnostics are kept in separate `poc_*` keys, not in BASE_COLUMNS.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re
from typing import Any

from .config import EMOTION_CLASSES

NUMERIC_COLUMNS = [
    "face_aspect_ratio",
    "jawline_angle",
    "cheek_width_ratio",
    "eye_size_ratio",
    "eye_distance_ratio",
    "eye_slant_angle",
    "eyebrow_thickness",
    "nose_length_ratio",
    "nose_width_ratio",
    "mouth_width_ratio",
    "lip_thickness_ratio",
    "smile_score",
]

BOOLEAN_COLUMNS = [
    "has_glasses",
    "has_facial_hair",
    "has_bangs",
]

# Real User_Face_Features columns (fixed 1:1)
BASE_COLUMNS = [
    "session_id",
    "image_url",
    "created_at",
    "face_aspect_ratio",
    "jawline_angle",
    "cheek_width_ratio",
    "eye_size_ratio",
    "eye_distance_ratio",
    "eye_slant_angle",
    "eyebrow_thickness",
    "nose_length_ratio",
    "nose_width_ratio",
    "mouth_width_ratio",
    "lip_thickness_ratio",
    "has_glasses",
    "has_facial_hair",
    "has_bangs",
    "dominant_color",
    "smile_score",
    "emotion_class",
]

POC_META_COLUMNS = [
    "poc_status",
    "poc_error_code",
    "poc_quality_score",
]

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass
class UserFaceFeaturesRow:
    session_id: str
    image_url: str
    created_at: str

    face_aspect_ratio: float
    jawline_angle: float
    cheek_width_ratio: float

    eye_size_ratio: float
    eye_distance_ratio: float
    eye_slant_angle: float
    eyebrow_thickness: float

    nose_length_ratio: float
    nose_width_ratio: float
    mouth_width_ratio: float
    lip_thickness_ratio: float

    has_glasses: bool
    has_facial_hair: bool
    has_bangs: bool

    dominant_color: str
    smile_score: float
    emotion_class: str

    def to_dict(self) -> dict:
        return asdict(self)


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return False


def default_row(session_id: str, image_url: str) -> dict:
    return UserFaceFeaturesRow(
        session_id=session_id,
        image_url=image_url,
        created_at=now_iso(),
        face_aspect_ratio=0.0,
        jawline_angle=0.0,
        cheek_width_ratio=0.0,
        eye_size_ratio=0.0,
        eye_distance_ratio=0.0,
        eye_slant_angle=0.5,
        eyebrow_thickness=0.0,
        nose_length_ratio=0.0,
        nose_width_ratio=0.0,
        mouth_width_ratio=0.0,
        lip_thickness_ratio=0.0,
        has_glasses=False,
        has_facial_hair=False,
        has_bangs=False,
        dominant_color="#808080",
        smile_score=0.5,
        emotion_class="무표정",
    ).to_dict()


def default_failed_row(session_id: str, image_url: str, error_code: str) -> dict:
    out = default_row(session_id=session_id, image_url=image_url)
    out["poc_status"] = "failed"
    out["poc_error_code"] = str(error_code)
    out["poc_quality_score"] = 0.0
    return out


def sanitize_row(row: dict[str, Any], keep_extra: bool = False) -> dict[str, Any]:
    """Clamp schema ranges and normalize categorical values.

    When keep_extra=True, non-schema keys (including poc_* meta) are preserved.
    """
    defaults = default_row(
        session_id=str(row.get("session_id", "")),
        image_url=str(row.get("image_url", "")),
    )
    out = {k: row.get(k, defaults[k]) for k in BASE_COLUMNS}

    session_id = str(out.get("session_id", "")).strip()
    out["session_id"] = session_id if session_id else "sess_unknown"
    out["image_url"] = str(out.get("image_url", "")).strip()
    created_at = str(out.get("created_at", "")).strip()
    out["created_at"] = created_at if created_at else now_iso()

    for col in NUMERIC_COLUMNS:
        value = _to_float(out.get(col, 0.0), 0.0)
        out[col] = round(max(0.0, min(1.0, value)), 4)

    for col in BOOLEAN_COLUMNS:
        out[col] = _to_bool(out.get(col, False))

    color = str(out.get("dominant_color", "#808080"))
    if not _HEX_COLOR_RE.match(color):
        color = "#808080"
    out["dominant_color"] = color.upper()

    if out.get("emotion_class") not in EMOTION_CLASSES:
        out["emotion_class"] = "무표정"

    if keep_extra:
        for key, value in row.items():
            if key not in out:
                out[key] = value

        if "poc_status" in out:
            status = str(out.get("poc_status", "failed")).lower()
            out["poc_status"] = status if status in ("success", "failed") else "failed"
        if "poc_error_code" in out:
            out["poc_error_code"] = str(out.get("poc_error_code", ""))
        if "poc_quality_score" in out:
            out["poc_quality_score"] = round(
                max(0.0, min(1.0, _to_float(out.get("poc_quality_score", 0.0), 0.0))),
                4,
            )

    return out
