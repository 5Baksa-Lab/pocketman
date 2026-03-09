"""
Step 7. 사용자 이미지 특징 추출 PoC 스크립트
입력: 사용자 이미지 폴더 (jpg/jpeg/png/webp)
출력:
  - User_Face_Features 실스키마(20컬럼) CSV
  - PoC 디버그 메타 CSV(poc_status/error/quality)
  - per-image JSON + 디버그 오버레이

실행 방법:
    python scripts/07_extract_user_features_poc.py --input-dir scripts/poc_images
    python scripts/07_extract_user_features_poc.py --input-dir scripts/poc_images --write-db
    python scripts/07_extract_user_features_poc.py --input-dir scripts/poc_images --limit 20
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - local env fallback
    def load_dotenv() -> bool:
        return False

from user_poc.schema import BASE_COLUMNS, POC_META_COLUMNS, sanitize_row

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
SAFE_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def collect_images(input_dir: Path) -> list[Path]:
    from user_poc.extractor import is_image_file

    if not input_dir.exists():
        return []
    files = [p for p in input_dir.rglob("*") if p.is_file() and is_image_file(p)]
    return sorted(files)


def write_csv(rows: list[dict], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=BASE_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in BASE_COLUMNS})


def write_debug_csv(rows: list[dict], csv_path: Path) -> None:
    fields = BASE_COLUMNS + POC_META_COLUMNS
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def get_db_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    try:
        import psycopg2  # type: ignore

        return psycopg2.connect(url)
    except ModuleNotFoundError:
        import psycopg  # type: ignore

        return psycopg.connect(url)


def upsert_to_db(rows: list[dict], table_name: str) -> None:
    if not SAFE_TABLE_NAME_RE.match(table_name):
        raise ValueError(f"허용되지 않는 테이블명입니다: {table_name}")

    success_rows = [r for r in rows if r.get("poc_status") == "success"]
    if not success_rows:
        log.warning("DB 저장할 success row가 없어 건너뜁니다.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    sql = f"""
        INSERT INTO {table_name} (
            session_id, image_url, created_at,
            face_aspect_ratio, jawline_angle, cheek_width_ratio,
            eye_size_ratio, eye_distance_ratio, eye_slant_angle, eyebrow_thickness,
            nose_length_ratio, nose_width_ratio, mouth_width_ratio, lip_thickness_ratio,
            has_glasses, has_facial_hair, has_bangs,
            dominant_color, smile_score, emotion_class
        ) VALUES (
            %(session_id)s, %(image_url)s, %(created_at)s,
            %(face_aspect_ratio)s, %(jawline_angle)s, %(cheek_width_ratio)s,
            %(eye_size_ratio)s, %(eye_distance_ratio)s, %(eye_slant_angle)s, %(eyebrow_thickness)s,
            %(nose_length_ratio)s, %(nose_width_ratio)s, %(mouth_width_ratio)s, %(lip_thickness_ratio)s,
            %(has_glasses)s, %(has_facial_hair)s, %(has_bangs)s,
            %(dominant_color)s, %(smile_score)s, %(emotion_class)s
        )
        ON CONFLICT (session_id) DO UPDATE SET
            image_url = EXCLUDED.image_url,
            created_at = EXCLUDED.created_at,
            face_aspect_ratio = EXCLUDED.face_aspect_ratio,
            jawline_angle = EXCLUDED.jawline_angle,
            cheek_width_ratio = EXCLUDED.cheek_width_ratio,
            eye_size_ratio = EXCLUDED.eye_size_ratio,
            eye_distance_ratio = EXCLUDED.eye_distance_ratio,
            eye_slant_angle = EXCLUDED.eye_slant_angle,
            eyebrow_thickness = EXCLUDED.eyebrow_thickness,
            nose_length_ratio = EXCLUDED.nose_length_ratio,
            nose_width_ratio = EXCLUDED.nose_width_ratio,
            mouth_width_ratio = EXCLUDED.mouth_width_ratio,
            lip_thickness_ratio = EXCLUDED.lip_thickness_ratio,
            has_glasses = EXCLUDED.has_glasses,
            has_facial_hair = EXCLUDED.has_facial_hair,
            has_bangs = EXCLUDED.has_bangs,
            dominant_color = EXCLUDED.dominant_color,
            smile_score = EXCLUDED.smile_score,
            emotion_class = EXCLUDED.emotion_class;
    """

    for row in success_rows:
        cursor.execute(sql, row)

    conn.commit()
    cursor.close()
    conn.close()
    log.info("DB upsert 완료: %d rows -> %s", len(success_rows), table_name)


def run(input_dir: Path, output_dir: Path, limit: int, write_db: bool, table_name: str) -> int:
    try:
        import cv2  # pylint: disable=import-outside-toplevel
        from user_poc.extractor import UserFaceFeatureExtractor  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError as exc:
        log.error("필수 의존성 모듈이 없습니다: %s", exc)
        log.error("먼저 `pip install -r scripts/requirements.txt` 를 실행하세요.")
        return 1

    image_paths = collect_images(input_dir)
    if limit > 0:
        image_paths = image_paths[:limit]

    if not image_paths:
        log.error("이미지 파일이 없습니다. --input-dir 경로를 확인하세요: %s", input_dir)
        return 1

    log.info("추출 대상 이미지: %d장", len(image_paths))

    json_dir = output_dir / "json"
    overlay_dir = output_dir / "overlays"
    json_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    extractor = UserFaceFeatureExtractor(min_detection_conf=0.5)
    rows: list[dict] = []

    for idx, image_path in enumerate(image_paths, start=1):
        row, image_bgr = extractor.extract(str(image_path))
        row = sanitize_row(row, keep_extra=True)
        rows.append(row)

        json_path = json_dir / f"{image_path.stem}.json"
        with json_path.open("w", encoding="utf-8") as fp:
            json.dump(row, fp, ensure_ascii=False, indent=2)

        if image_bgr is not None:
            overlay_img = extractor.draw_overlay(image_bgr, row)
            overlay_path = overlay_dir / f"{image_path.stem}_overlay.jpg"
            cv2.imwrite(str(overlay_path), overlay_img)

        log.info(
            "[%d/%d] %s | status=%s | emotion=%s | smile=%.2f | quality=%.2f",
            idx,
            len(image_paths),
            image_path.name,
            row.get("poc_status", "failed"),
            row.get("emotion_class"),
            float(row.get("smile_score", 0.0)),
            float(row.get("poc_quality_score", 0.0)),
        )

    csv_path = output_dir / "user_face_features_poc.csv"
    debug_csv_path = output_dir / "user_face_features_poc_debug.csv"
    write_csv(rows, csv_path)
    write_debug_csv(rows, debug_csv_path)

    success_count = sum(1 for r in rows if r.get("poc_status") == "success")
    fail_count = len(rows) - success_count
    success_rate = (success_count / len(rows)) * 100.0 if rows else 0.0

    log.info("CSV 저장: %s", csv_path)
    log.info("Debug CSV 저장: %s", debug_csv_path)
    log.info("추출 결과: success=%d fail=%d success_rate=%.1f%%", success_count, fail_count, success_rate)

    if write_db:
        try:
            upsert_to_db(rows, table_name=table_name)
        except Exception as exc:
            log.error("DB upsert 실패: %s", exc)
            return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User_Face_Features 추출 PoC")
    parser.add_argument("--input-dir", required=True, help="입력 이미지 디렉토리")
    parser.add_argument("--output-dir", default="outputs/user_poc", help="결과 저장 디렉토리")
    parser.add_argument("--limit", type=int, default=0, help="상위 N장만 처리 (0=전체)")
    parser.add_argument("--write-db", action="store_true", help="추출 성공 행을 DB에 upsert")
    parser.add_argument("--table-name", default="user_face_features", help="DB 테이블명")

    args = parser.parse_args()

    raise SystemExit(
        run(
            input_dir=Path(args.input_dir),
            output_dir=Path(args.output_dir),
            limit=args.limit,
            write_db=args.write_db,
            table_name=args.table_name,
        )
    )
