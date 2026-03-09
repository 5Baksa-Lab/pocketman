"""
CV Adapter — 업로드된 이미지에서 28차원 사용자 벡터를 생성
scripts/user_poc/extractor.py 의 MediaPipe 로직을 재사용

28차원 벡터 구성 (포켓몬 벡터와 동일한 순서):
  [0-9]   visual 10차원
  [10-18] impression 9차원 (visual에서 규칙 기반 산출)
  [19-26] type_affinity 8차원 (impression에서 역산)
  [27]    glasses 1차원
"""
import sys
import numpy as np
import os
from pathlib import Path

# scripts 폴더를 path에 추가 (로컬/컨테이너 레이아웃 모두 대응)
_THIS_FILE = Path(__file__).resolve()
_SCRIPT_CANDIDATES = [
    _THIS_FILE.parents[3] / "scripts",  # <repo>/scripts
    _THIS_FILE.parents[2] / "scripts",  # /app/scripts (container)
    Path("/app/scripts"),
]
SCRIPTS_DIR = next((p for p in _SCRIPT_CANDIDATES if p.exists()), _SCRIPT_CANDIDATES[0])
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from user_poc.extractor import UserFaceFeatureExtractor  # type: ignore
from shared.feature_mapping import (  # type: ignore
    calc_impression_from_visual,
    calc_type_affinity_from_impression,
)

from app.core.errors import FaceNotDetectedError, LowQualityError


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


# ── MediaPipe raw → visual 10차원 스코어 변환 ─────────────────────────────────
def _raw_to_visual(raw: dict) -> dict:
    """
    user_poc extractor의 원시 측정값을 포켓몬 벡터와 동일한
    10차원 visual 스코어로 변환
    """
    def c(v): return _clamp(v)

    return {
        "eye_size_score":          c(raw.get("eye_size_ratio", 0.5)),
        "eye_distance_score":      c(raw.get("eye_distance_ratio", 0.5)),
        # eye_roundness: eyebrow_thickness로 근사 (두꺼울수록 날카로운 느낌 → 역산)
        "eye_roundness_score":     c(1.0 - raw.get("eyebrow_thickness", 0.5)),
        "eye_tail_score":          c(raw.get("eye_slant_angle", 0.5)),
        # face_roundness: jawline_angle (둥글수록 높음)
        "face_roundness_score":    c(raw.get("jawline_angle", 0.5)),
        # face_proportion: face_aspect_ratio 역산 (세로형일수록 높음)
        "face_proportion_score":   c(1.0 - raw.get("face_aspect_ratio", 0.5)),
        # feature_size: nose_width + mouth_width 평균
        "feature_size_score":      c((raw.get("nose_width_ratio", 0.3) + raw.get("mouth_width_ratio", 0.5)) / 2),
        # feature_emphasis: lip_thickness + nose_length 평균
        "feature_emphasis_score":  c((raw.get("lip_thickness_ratio", 0.3) + raw.get("nose_length_ratio", 0.4)) / 2),
        "mouth_curve_score":       c(raw.get("smile_score", 0.5)),
        # overall_symmetry: cheek_width로 근사 (대칭일수록 cheek 비율이 안정적)
        "overall_symmetry":        c(raw.get("cheek_width_ratio", 0.7)),
        "has_glasses":             bool(raw.get("has_glasses", False)),
    }


# ── 최종 28차원 벡터 생성 ──────────────────────────────────────────────────────
def build_user_vector(image_bytes: bytes) -> tuple[np.ndarray, dict]:
    """
    이미지 바이트 → 28차원 L2 정규화 벡터

    Returns:
        (vector: np.ndarray shape(28,), raw_features: dict)
    """
    import tempfile

    # extractor가 파일 경로를 요구하므로 임시 파일 사용
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    extractor = UserFaceFeatureExtractor()
    try:
        result, _ = extractor.extract(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if result.get("poc_status") == "failed":
        error_code = result.get("poc_error_code", "")
        if "no_face" in error_code:
            raise FaceNotDetectedError()
        if "multi_face" in error_code:
            from app.core.errors import MultipleFacesError
            raise MultipleFacesError()
        raise FaceNotDetectedError()

    quality = float(result.get("poc_quality_score", 0.0))
    if quality < 0.15:
        raise LowQualityError()

    visual = _raw_to_visual(result)
    impression = calc_impression_from_visual(visual)
    affinity = calc_type_affinity_from_impression(impression)

    vector = np.array([
        # [0-9] visual
        visual["eye_size_score"],
        visual["eye_distance_score"],
        visual["eye_roundness_score"],
        visual["eye_tail_score"],
        visual["face_roundness_score"],
        visual["face_proportion_score"],
        visual["feature_size_score"],
        visual["feature_emphasis_score"],
        visual["mouth_curve_score"],
        visual["overall_symmetry"],
        # [10-18] impression
        impression["cute"],
        impression["calm"],
        impression["smart"],
        impression["fierce"],
        impression["gentle"],
        impression["lively"],
        impression["innocent"],
        impression["confident"],
        impression["unique"],
        # [19-26] type_affinity
        affinity["water"],
        affinity["fire"],
        affinity["grass"],
        affinity["electric"],
        affinity["psychic"],
        affinity["normal"],
        affinity["fighting"],
        affinity["ghost"],
        # [27] glasses
        1.0 if visual["has_glasses"] else 0.0,
    ], dtype=np.float32)

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    raw_features = {**result, "visual": visual, "impression": impression, "affinity": affinity}
    return vector, raw_features
