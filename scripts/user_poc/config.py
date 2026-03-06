"""Constants for MediaPipe landmark indices and heuristic thresholds."""

from __future__ import annotations

# MediaPipe face mesh landmark indices
LANDMARK = {
    "left_jaw": 234,
    "right_jaw": 454,
    "chin": 152,
    "forehead": 10,
    "left_cheek": 234,
    "right_cheek": 454,
    # eye
    "left_eye_outer": 33,
    "left_eye_inner": 133,
    "left_eye_upper": 159,
    "left_eye_lower": 145,
    "right_eye_outer": 263,
    "right_eye_inner": 362,
    "right_eye_upper": 386,
    "right_eye_lower": 374,
    # eyebrow (approx)
    "left_brow_mid": 105,
    "right_brow_mid": 334,
    # nose
    "nose_root": 168,
    "nose_tip": 1,
    "nose_left": 98,
    "nose_right": 327,
    # mouth
    "mouth_left": 61,
    "mouth_right": 291,
    "mouth_upper": 13,
    "mouth_lower": 14,
}

# Numeric normalization ranges for user feature schema (heuristic)
RANGE = {
    "face_aspect_ratio": (0.60, 1.45),
    "jawline_angle": (55.0, 145.0),
    "cheek_width_ratio": (0.45, 1.25),
    "eye_size_ratio": (0.018, 0.120),
    "eye_distance_ratio": (0.12, 0.55),
    "eye_slant_angle": (-20.0, 20.0),
    "eyebrow_thickness": (0.02, 0.12),
    "nose_length_ratio": (0.08, 0.45),
    "nose_width_ratio": (0.05, 0.35),
    "mouth_width_ratio": (0.12, 0.55),
    "lip_thickness_ratio": (0.02, 0.28),
    "smile_curve": (-0.030, 0.040),
    "mouth_open_ratio": (0.01, 0.25),
}

EMOTION_CLASSES = (
    "기쁨",
    "무표정",
    "분노",
    "신비",
    "온화",
    "슬픔",
    "공포",
)

# Heuristic thresholds
THRESHOLD = {
    "min_face_pixels": 80,
    "glasses_edge_density": 0.12,
    "facial_hair_dark_ratio": 0.22,
    "bangs_dark_ratio": 0.33,
    "sharpness_warn": 50.0,
}
