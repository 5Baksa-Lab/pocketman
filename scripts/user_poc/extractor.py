"""User image feature extractor for User_Face_Features PoC."""

from __future__ import annotations

import math
import uuid
from pathlib import Path

import cv2
import numpy as np
try:
    import mediapipe as mp  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    mp = None  # type: ignore

from .config import EMOTION_CLASSES, LANDMARK, RANGE, THRESHOLD
from .schema import UserFaceFeaturesRow, default_failed_row, now_iso, sanitize_row


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize(value: float, lo: float, hi: float, invert: bool = False) -> float:
    if hi <= lo:
        return 0.0
    ratio = (value - lo) / (hi - lo)
    ratio = _clamp(ratio, 0.0, 1.0)
    return 1.0 - ratio if invert else ratio


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _angle_at(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> float:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return 90.0
    cosine = _clamp(dot / (mag_ba * mag_bc), -1.0, 1.0)
    return math.degrees(math.acos(cosine))


def _to_hex_color(bgr_color: np.ndarray) -> str:
    b, g, r = [int(x) for x in bgr_color]
    return f"#{r:02X}{g:02X}{b:02X}"


def _dominant_color_hex(image_bgr: np.ndarray) -> str:
    pixels = image_bgr.reshape((-1, 3)).astype(np.float32)
    if len(pixels) == 0:
        return "#808080"

    k = 3
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.2)
    _compactness, labels, centers = cv2.kmeans(
        pixels,
        k,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    counts = np.bincount(labels.flatten(), minlength=k)
    dominant_idx = int(np.argmax(counts))
    return _to_hex_color(centers[dominant_idx])


def _emotion_from_scores(smile_score: float, eye_slant_score: float, eye_size_score: float) -> str:
    if smile_score >= 0.72:
        return "기쁨"
    if smile_score < 0.20 and eye_size_score > 0.75:
        return "공포"
    if smile_score < 0.28 and eye_slant_score > 0.62:
        return "분노"
    if smile_score < 0.30 and eye_slant_score < 0.35:
        return "슬픔"
    if 0.55 <= smile_score < 0.72 and eye_slant_score <= 0.5:
        return "온화"
    if eye_size_score > 0.68 and 0.35 <= smile_score <= 0.58:
        return "신비"
    return "무표정"


class UserFaceFeatureExtractor:
    def __init__(self, min_detection_conf: float = 0.5):
        self._backend = "opencv_haar"
        self._face_mesh = None
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
        )

        if (
            mp is not None
            and hasattr(mp, "solutions")
            and hasattr(mp.solutions, "face_mesh")
        ):
            self._backend = "mediapipe_face_mesh"
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = self._mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=2,
                refine_landmarks=True,
                min_detection_confidence=min_detection_conf,
            )

    def _lm_px(self, landmarks, idx: int, width: int, height: int) -> tuple[int, int]:
        lm = landmarks[idx]
        return int(lm.x * width), int(lm.y * height)

    def extract(self, image_path: str) -> tuple[dict, np.ndarray | None]:
        image_path = str(image_path)
        session_id = f"sess_{uuid.uuid4().hex[:10]}"

        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            return default_failed_row(session_id, image_path, "IMAGE_READ_FAIL"), None

        if self._backend != "mediapipe_face_mesh" or self._face_mesh is None:
            return self._extract_with_haar(
                session_id=session_id,
                image_path=image_path,
                image_bgr=image_bgr,
            )

        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return default_failed_row(session_id, image_path, "FACE_NOT_DETECTED"), image_bgr
        if len(results.multi_face_landmarks) > 1:
            return default_failed_row(session_id, image_path, "MULTIPLE_FACES"), image_bgr

        lms = results.multi_face_landmarks[0].landmark

        # Face bbox from all landmarks
        xs = [int(p.x * w) for p in lms]
        ys = [int(p.y * h) for p in lms]
        x0, x1 = max(0, min(xs)), min(w - 1, max(xs))
        y0, y1 = max(0, min(ys)), min(h - 1, max(ys))
        face_w = max(1, x1 - x0)
        face_h = max(1, y1 - y0)

        if face_w < THRESHOLD["min_face_pixels"] or face_h < THRESHOLD["min_face_pixels"]:
            return default_failed_row(session_id, image_path, "FACE_TOO_SMALL"), image_bgr

        p = {
            name: self._lm_px(lms, idx, w, h)
            for name, idx in LANDMARK.items()
        }

        # Core geometry
        raw_face_aspect = face_w / face_h
        raw_jaw_angle = _angle_at(p["left_jaw"], p["chin"], p["right_jaw"])
        raw_cheek = _distance(p["left_cheek"], p["right_cheek"]) / face_h

        left_eye_h = _distance(p["left_eye_upper"], p["left_eye_lower"])
        right_eye_h = _distance(p["right_eye_upper"], p["right_eye_lower"])
        avg_eye_h = (left_eye_h + right_eye_h) / 2.0
        raw_eye_size = avg_eye_h / face_h

        raw_eye_dist = _distance(p["left_eye_inner"], p["right_eye_inner"]) / face_w

        left_slant_deg = math.degrees(
            math.atan2(
                p["left_eye_inner"][1] - p["left_eye_outer"][1],
                p["left_eye_inner"][0] - p["left_eye_outer"][0],
            )
        )
        right_slant_deg = math.degrees(
            math.atan2(
                p["right_eye_outer"][1] - p["right_eye_inner"][1],
                p["right_eye_outer"][0] - p["right_eye_inner"][0],
            )
        )
        raw_eye_slant_deg = (left_slant_deg + right_slant_deg) / 2.0

        brow_eye_l = _distance(p["left_brow_mid"], p["left_eye_upper"]) / face_h
        brow_eye_r = _distance(p["right_brow_mid"], p["right_eye_upper"]) / face_h
        raw_brow_gap = (brow_eye_l + brow_eye_r) / 2.0

        raw_nose_len = _distance(p["nose_root"], p["nose_tip"]) / face_h
        raw_nose_w = _distance(p["nose_left"], p["nose_right"]) / face_w
        mouth_w_px = _distance(p["mouth_left"], p["mouth_right"])
        raw_mouth_w = mouth_w_px / face_w

        raw_lip_thickness = _distance(p["mouth_upper"], p["mouth_lower"]) / max(1.0, mouth_w_px)

        # Smile score from mouth curve + openness
        corner_avg_y = (p["mouth_left"][1] + p["mouth_right"][1]) / 2.0
        center_mouth_y = (p["mouth_upper"][1] + p["mouth_lower"][1]) / 2.0
        raw_smile_curve = (center_mouth_y - corner_avg_y) / face_h
        smile_curve_score = _normalize(raw_smile_curve, *RANGE["smile_curve"])
        mouth_open_ratio = _distance(p["mouth_upper"], p["mouth_lower"]) / max(1.0, mouth_w_px)
        mouth_open_score = _normalize(mouth_open_ratio, *RANGE["mouth_open_ratio"])
        smile_score = _clamp((smile_curve_score * 0.75) + (mouth_open_score * 0.25), 0.0, 1.0)

        # Heuristic boolean features
        face_roi = image_bgr[y0:y1, x0:x1]
        gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if face_roi.size else None

        has_glasses = False
        has_facial_hair = False
        has_bangs = False

        if gray_face is not None and gray_face.size > 0:
            edges = cv2.Canny(gray_face, 50, 150)
            edge_density = float(np.count_nonzero(edges)) / float(edges.size)
            has_glasses = edge_density > THRESHOLD["glasses_edge_density"]

            hsv_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            # lower face region
            lower = hsv_face[int(hsv_face.shape[0] * 0.60):, :]
            if lower.size > 0:
                dark_mask = (lower[:, :, 2] < 80) & (lower[:, :, 1] > 30)
                dark_ratio = float(np.count_nonzero(dark_mask)) / float(dark_mask.size)
                has_facial_hair = dark_ratio > THRESHOLD["facial_hair_dark_ratio"]

            # forehead region
            upper = hsv_face[: max(1, int(hsv_face.shape[0] * 0.28)), :]
            if upper.size > 0:
                hair_like = (upper[:, :, 2] < 90) & (upper[:, :, 1] > 20)
                hair_ratio = float(np.count_nonzero(hair_like)) / float(hair_like.size)
                has_bangs = hair_ratio > THRESHOLD["bangs_dark_ratio"]

        # Quality score heuristic
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        face_area_ratio = (face_w * face_h) / float(w * h)
        quality = _clamp((face_area_ratio * 1.6) + _normalize(sharpness, 30.0, 220.0) * 0.4, 0.0, 1.0)

        row = UserFaceFeaturesRow(
            session_id=session_id,
            image_url=image_path,
            created_at=now_iso(),
            face_aspect_ratio=_normalize(raw_face_aspect, *RANGE["face_aspect_ratio"]),
            jawline_angle=_normalize(raw_jaw_angle, *RANGE["jawline_angle"]),
            cheek_width_ratio=_normalize(raw_cheek, *RANGE["cheek_width_ratio"]),
            eye_size_ratio=_normalize(raw_eye_size, *RANGE["eye_size_ratio"]),
            eye_distance_ratio=_normalize(raw_eye_dist, *RANGE["eye_distance_ratio"]),
            eye_slant_angle=_normalize(raw_eye_slant_deg, *RANGE["eye_slant_angle"]),
            eyebrow_thickness=_normalize(raw_brow_gap, *RANGE["eyebrow_thickness"], invert=True),
            nose_length_ratio=_normalize(raw_nose_len, *RANGE["nose_length_ratio"]),
            nose_width_ratio=_normalize(raw_nose_w, *RANGE["nose_width_ratio"]),
            mouth_width_ratio=_normalize(raw_mouth_w, *RANGE["mouth_width_ratio"]),
            lip_thickness_ratio=_normalize(raw_lip_thickness, *RANGE["lip_thickness_ratio"]),
            has_glasses=bool(has_glasses),
            has_facial_hair=bool(has_facial_hair),
            has_bangs=bool(has_bangs),
            dominant_color=_dominant_color_hex(image_bgr),
            smile_score=smile_score,
            emotion_class=_emotion_from_scores(
                smile_score=smile_score,
                eye_slant_score=_normalize(raw_eye_slant_deg, *RANGE["eye_slant_angle"]),
                eye_size_score=_normalize(raw_eye_size, *RANGE["eye_size_ratio"]),
            ),
        ).to_dict()

        # Keep emotion class within schema list
        if row["emotion_class"] not in EMOTION_CLASSES:
            row["emotion_class"] = "무표정"

        row["poc_status"] = "success"
        row["poc_error_code"] = ""
        row["poc_quality_score"] = quality
        return sanitize_row(row, keep_extra=True), image_bgr

    def _extract_with_haar(
        self,
        session_id: str,
        image_path: str,
        image_bgr: np.ndarray,
    ) -> tuple[dict, np.ndarray]:
        h, w = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        if self._face_cascade is None or self._face_cascade.empty():
            return default_failed_row(session_id, image_path, "FACE_DETECTOR_UNAVAILABLE"), image_bgr

        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.12,
            minNeighbors=5,
            minSize=(THRESHOLD["min_face_pixels"], THRESHOLD["min_face_pixels"]),
        )

        if len(faces) == 0:
            return default_failed_row(session_id, image_path, "FACE_NOT_DETECTED"), image_bgr
        if len(faces) > 1:
            return default_failed_row(session_id, image_path, "MULTIPLE_FACES"), image_bgr

        x0, y0, face_w, face_h = [int(v) for v in faces[0]]
        x1 = min(w, x0 + face_w)
        y1 = min(h, y0 + face_h)
        x0 = max(0, x0)
        y0 = max(0, y0)
        face_w = max(1, x1 - x0)
        face_h = max(1, y1 - y0)

        if face_w < THRESHOLD["min_face_pixels"] or face_h < THRESHOLD["min_face_pixels"]:
            return default_failed_row(session_id, image_path, "FACE_TOO_SMALL"), image_bgr

        face_roi = image_bgr[y0:y1, x0:x1]
        gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        # Eye proxies from Haar eye detector (fallback when MediaPipe face mesh is unavailable)
        raw_eye_size = 0.045
        raw_eye_dist = 0.30
        raw_eye_slant_deg = 0.0
        raw_brow_gap = 0.055

        if self._eye_cascade is not None and not self._eye_cascade.empty():
            upper_gray = gray_face[: max(1, int(face_h * 0.58)), :]
            eyes = self._eye_cascade.detectMultiScale(
                upper_gray,
                scaleFactor=1.10,
                minNeighbors=4,
                minSize=(max(8, int(face_w * 0.08)), max(8, int(face_h * 0.05))),
            )

            if len(eyes) >= 2:
                eyes = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
                eyes = sorted(eyes, key=lambda e: e[0])
                left, right = eyes[0], eyes[1]

                left_cx = left[0] + (left[2] / 2.0)
                left_cy = left[1] + (left[3] / 2.0)
                right_cx = right[0] + (right[2] / 2.0)
                right_cy = right[1] + (right[3] / 2.0)

                raw_eye_size = ((left[3] + right[3]) / 2.0) / face_h
                raw_eye_dist = abs(right_cx - left_cx) / face_w
                raw_eye_slant_deg = math.degrees(
                    math.atan2((right_cy - left_cy), max(1.0, (right_cx - left_cx)))
                )
                raw_brow_gap = raw_eye_size * 1.35

        # Geometry proxies
        raw_face_aspect = face_w / face_h
        raw_jaw_angle = 95.0
        raw_cheek = face_w / face_h

        # Nose / mouth proxies (ROI heuristics)
        raw_nose_len = 0.23
        raw_nose_w = 0.16
        raw_mouth_w = 0.34
        raw_lip_thickness = 0.10
        smile_score = 0.50

        mouth_y0 = int(face_h * 0.62)
        mouth_y1 = int(face_h * 0.92)
        mouth_x0 = int(face_w * 0.20)
        mouth_x1 = int(face_w * 0.80)
        mouth_roi = gray_face[mouth_y0:mouth_y1, mouth_x0:mouth_x1]
        if mouth_roi.size > 0:
            mouth_edges = cv2.Canny(mouth_roi, 60, 160)
            edge_ratio = float(np.count_nonzero(mouth_edges)) / float(mouth_edges.size)
            smile_score = _normalize(edge_ratio, 0.03, 0.20)

        has_glasses = False
        has_facial_hair = False
        has_bangs = False

        if gray_face.size > 0:
            edges = cv2.Canny(gray_face, 50, 150)
            edge_density = float(np.count_nonzero(edges)) / float(edges.size)
            has_glasses = edge_density > THRESHOLD["glasses_edge_density"]

            hsv_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            lower = hsv_face[int(hsv_face.shape[0] * 0.60):, :]
            if lower.size > 0:
                dark_mask = (lower[:, :, 2] < 80) & (lower[:, :, 1] > 30)
                dark_ratio = float(np.count_nonzero(dark_mask)) / float(dark_mask.size)
                has_facial_hair = dark_ratio > THRESHOLD["facial_hair_dark_ratio"]

            upper = hsv_face[: max(1, int(hsv_face.shape[0] * 0.28)), :]
            if upper.size > 0:
                hair_like = (upper[:, :, 2] < 90) & (upper[:, :, 1] > 20)
                hair_ratio = float(np.count_nonzero(hair_like)) / float(hair_like.size)
                has_bangs = hair_ratio > THRESHOLD["bangs_dark_ratio"]

        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        face_area_ratio = (face_w * face_h) / float(w * h)
        quality = _clamp(
            (face_area_ratio * 1.6) + _normalize(sharpness, 30.0, 220.0) * 0.4,
            0.0,
            1.0,
        )

        eye_slant_score = _normalize(raw_eye_slant_deg, *RANGE["eye_slant_angle"])
        eye_size_score = _normalize(raw_eye_size, *RANGE["eye_size_ratio"])

        row = UserFaceFeaturesRow(
            session_id=session_id,
            image_url=image_path,
            created_at=now_iso(),
            face_aspect_ratio=_normalize(raw_face_aspect, *RANGE["face_aspect_ratio"]),
            jawline_angle=_normalize(raw_jaw_angle, *RANGE["jawline_angle"]),
            cheek_width_ratio=_normalize(raw_cheek, *RANGE["cheek_width_ratio"]),
            eye_size_ratio=eye_size_score,
            eye_distance_ratio=_normalize(raw_eye_dist, *RANGE["eye_distance_ratio"]),
            eye_slant_angle=eye_slant_score,
            eyebrow_thickness=_normalize(raw_brow_gap, *RANGE["eyebrow_thickness"], invert=True),
            nose_length_ratio=_normalize(raw_nose_len, *RANGE["nose_length_ratio"]),
            nose_width_ratio=_normalize(raw_nose_w, *RANGE["nose_width_ratio"]),
            mouth_width_ratio=_normalize(raw_mouth_w, *RANGE["mouth_width_ratio"]),
            lip_thickness_ratio=_normalize(raw_lip_thickness, *RANGE["lip_thickness_ratio"]),
            has_glasses=bool(has_glasses),
            has_facial_hair=bool(has_facial_hair),
            has_bangs=bool(has_bangs),
            dominant_color=_dominant_color_hex(image_bgr),
            smile_score=_clamp(smile_score, 0.0, 1.0),
            emotion_class=_emotion_from_scores(
                smile_score=_clamp(smile_score, 0.0, 1.0),
                eye_slant_score=eye_slant_score,
                eye_size_score=eye_size_score,
            ),
        ).to_dict()

        if row["emotion_class"] not in EMOTION_CLASSES:
            row["emotion_class"] = "무표정"

        row["poc_status"] = "success"
        row["poc_error_code"] = ""
        row["poc_quality_score"] = quality
        return sanitize_row(row, keep_extra=True), image_bgr

    @staticmethod
    def draw_overlay(image_bgr: np.ndarray, row: dict) -> np.ndarray:
        out = image_bgr.copy()
        status = row.get("poc_status", row.get("extraction_status", ""))
        text = [
            f"session={row.get('session_id', '')}",
            f"status={status}",
            f"smile={row.get('smile_score', 0):.2f} emotion={row.get('emotion_class', '무표정')}",
            f"glasses={int(bool(row.get('has_glasses')))} facial_hair={int(bool(row.get('has_facial_hair')))} bangs={int(bool(row.get('has_bangs')))}",
        ]
        y = 24
        for line in text:
            cv2.putText(out, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2, cv2.LINE_AA)
            y += 24
        return out


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
