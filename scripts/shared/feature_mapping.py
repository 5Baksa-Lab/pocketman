"""Shared feature mapping helpers used by both scripts and backend."""

from __future__ import annotations

from typing import Mapping


def clamp01(value: float) -> float:
    """Clamp a float into [0.0, 1.0]."""
    return max(0.0, min(1.0, float(value)))


def calc_impression_from_visual(visual: Mapping[str, float | bool]) -> dict[str, float]:
    """Derive 9 impression dimensions from visual feature scores."""
    eye_sz = float(visual.get("eye_size_score", 0.5))
    eye_dist = float(visual.get("eye_distance_score", 0.5))
    eye_round = float(visual.get("eye_roundness_score", 0.5))
    eye_tail = float(visual.get("eye_tail_score", 0.5))
    face_rnd = float(visual.get("face_roundness_score", 0.5))
    face_prop = float(visual.get("face_proportion_score", 0.5))
    feat_sz = float(visual.get("feature_size_score", 0.5))
    feat_emph = float(visual.get("feature_emphasis_score", 0.5))
    mouth = float(visual.get("mouth_curve_score", 0.5))
    symmetry = float(visual.get("overall_symmetry", 0.7))
    glasses = 1.0 if bool(visual.get("has_glasses", False)) else 0.0

    calm_mouth = 1.0 - abs(mouth - 0.5) * 2.0
    calm_tail = 1.0 - eye_tail
    eye_extremity = abs(eye_tail - 0.5) * 2.0

    return {
        "cute": clamp01(eye_sz * 0.40 + face_rnd * 0.30 + mouth * 0.30),
        "calm": clamp01(calm_mouth * 0.35 + symmetry * 0.35 + calm_tail * 0.30),
        "smart": clamp01(glasses * 0.50 + (1.0 - eye_dist) * 0.30 + (1.0 - eye_round) * 0.20),
        "fierce": clamp01(eye_tail * 0.45 + (1.0 - face_rnd) * 0.30 + feat_emph * 0.25),
        "gentle": clamp01(mouth * 0.40 + face_rnd * 0.30 + (1.0 - eye_tail) * 0.30),
        "lively": clamp01(mouth * 0.40 + eye_sz * 0.30 + feat_emph * 0.30),
        "innocent": clamp01(face_rnd * 0.40 + eye_round * 0.30 + (1.0 - feat_sz) * 0.30),
        "confident": clamp01((1.0 - face_prop) * 0.35 + (1.0 - face_rnd) * 0.35 + feat_emph * 0.30),
        "unique": clamp01(eye_extremity * 0.40 + feat_emph * 0.30 + glasses * 0.30),
    }


def calc_type_affinity_from_impression(impression: Mapping[str, float]) -> dict[str, float]:
    """Derive 8 type-affinity dimensions from impression scores."""
    return {
        "water": clamp01(float(impression.get("calm", 0.5)) * 0.6 + float(impression.get("gentle", 0.5)) * 0.4),
        "fire": clamp01(float(impression.get("fierce", 0.5)) * 0.5 + float(impression.get("lively", 0.5)) * 0.5),
        "grass": clamp01(float(impression.get("gentle", 0.5)) * 0.6 + float(impression.get("calm", 0.5)) * 0.4),
        "electric": clamp01(float(impression.get("smart", 0.5)) * 0.6 + float(impression.get("lively", 0.5)) * 0.4),
        "psychic": clamp01(float(impression.get("smart", 0.5)) * 0.4 + float(impression.get("unique", 0.5)) * 0.6),
        "normal": clamp01(float(impression.get("innocent", 0.5)) * 0.6 + float(impression.get("gentle", 0.5)) * 0.4),
        "fighting": clamp01(float(impression.get("confident", 0.5)) * 0.7 + float(impression.get("fierce", 0.5)) * 0.3),
        "ghost": clamp01(float(impression.get("unique", 0.5)) * 0.5 + float(impression.get("calm", 0.5)) * 0.5),
    }


def impression_to_db_scores(impression: Mapping[str, float]) -> dict[str, float]:
    """Convert impression keys (`cute`) to DB column keys (`cute_score`)."""
    return {f"{key}_score": round(float(value), 3) for key, value in impression.items()}

