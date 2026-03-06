"""
Step 8. 사용자 이미지 추출 PoC 검증 스크립트
입력:
  - Step 7 결과 CSV (User_Face_Features 실스키마 20컬럼)
  - Step 7 디버그 CSV(선택, poc_status/error/quality)
출력: 스키마/범위 + (옵션) 성공률/품질 검증 리포트

실행 방법:
    python scripts/08_validate_user_extraction_poc.py --csv outputs/user_poc/user_face_features_poc.csv
    python scripts/08_validate_user_extraction_poc.py --csv outputs/user_poc/user_face_features_poc.csv --strict
    python scripts/08_validate_user_extraction_poc.py --csv outputs/user_poc/user_face_features_poc.csv --debug-csv outputs/user_poc/user_face_features_poc_debug.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
from pathlib import Path

from user_poc.config import EMOTION_CLASSES
from user_poc.schema import BASE_COLUMNS, NUMERIC_COLUMNS, POC_META_COLUMNS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        return list(reader)


def to_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def validate(
    rows: list[dict],
    debug_rows: list[dict] | None,
    min_success_rate: float,
) -> tuple[int, int, int]:
    total = len(rows)
    errors = 0
    warnings = 0

    if total == 0:
        log.error("검증 대상 row가 0개입니다.")
        return 1, 0, 0

    # Required columns (real schema)
    row_cols = set(rows[0].keys())
    missing = [c for c in BASE_COLUMNS if c not in row_cols]
    if missing:
        log.error("필수 컬럼 누락: %s", missing)
        errors += len(missing)

    # Row-level checks for all feature rows
    for idx, row in enumerate(rows, start=1):
        sid = row.get("session_id", f"row{idx}")

        for col in NUMERIC_COLUMNS:
            v = to_float(row.get(col, ""), -1.0)
            if not (0.0 <= v <= 1.0):
                log.error("[%s] 범위 오류: %s=%s", sid, col, row.get(col))
                errors += 1

        color = row.get("dominant_color", "")
        if not HEX_COLOR_RE.match(color):
            log.error("[%s] 색상 형식 오류: dominant_color=%s", sid, color)
            errors += 1

        emo = row.get("emotion_class", "")
        if emo not in EMOTION_CLASSES:
            log.error("[%s] emotion_class 허용값 오류: %s", sid, emo)
            errors += 1

    # Debug checks (optional)
    if debug_rows:
        debug_cols = set(debug_rows[0].keys())
        required_debug = ["session_id"] + POC_META_COLUMNS
        missing_debug = [c for c in required_debug if c not in debug_cols]
        if missing_debug:
            log.error("debug CSV 필수 컬럼 누락: %s", missing_debug)
            errors += len(missing_debug)
        else:
            debug_map = {r.get("session_id", ""): r for r in debug_rows}
            success_count = 0
            failed_count = 0

            for row in rows:
                sid = row.get("session_id", "")
                dbg = debug_map.get(sid)
                if not dbg:
                    log.warning("[%s] debug row가 없습니다.", sid)
                    warnings += 1
                    continue

                status = str(dbg.get("poc_status", "failed")).lower()
                if status == "success":
                    success_count += 1
                elif status == "failed":
                    failed_count += 1
                    if not str(dbg.get("poc_error_code", "")):
                        log.warning("[%s] failed row에 poc_error_code 누락", sid)
                        warnings += 1
                else:
                    log.error("[%s] poc_status 허용값 오류: %s", sid, status)
                    errors += 1

                q = to_float(dbg.get("poc_quality_score", ""), -1.0)
                if not (0.0 <= q <= 1.0):
                    log.error("[%s] 범위 오류: poc_quality_score=%s", sid, dbg.get("poc_quality_score"))
                    errors += 1
                elif q < 0.25:
                    log.warning("[%s] 품질 점수 낮음: poc_quality_score=%.3f", sid, q)
                    warnings += 1

            known = success_count + failed_count
            if known == 0:
                log.error("debug CSV에서 success/failed 상태를 계산할 수 없습니다.")
                errors += 1
            else:
                success_rate = (success_count / known) * 100.0
                log.info(
                    "행 수: %d | success: %d | failed: %d | success_rate: %.1f%%",
                    known,
                    success_count,
                    failed_count,
                    success_rate,
                )
                if success_rate < min_success_rate:
                    log.error("성공률 미달: %.1f%% < %.1f%%", success_rate, min_success_rate)
                    errors += 1
    else:
        log.warning("debug CSV가 없어 성공률/품질 검증을 생략합니다.")
        warnings += 1

    # Quick stats
    means = {}
    for col in NUMERIC_COLUMNS:
        vals = [to_float(r.get(col, "0"), 0.0) for r in rows]
        means[col] = sum(vals) / len(rows)

    log.info("요약 평균값:")
    for col in ["face_aspect_ratio", "eye_size_ratio", "eye_slant_angle", "smile_score"]:
        log.info("  - %s: %.4f", col, means[col])

    return errors, warnings, total


def run(csv_path: Path, debug_csv_path: Path | None, strict: bool, min_success_rate: float) -> int:
    if not csv_path.exists():
        log.error("CSV 파일이 없습니다: %s", csv_path)
        return 1

    rows = load_rows(csv_path)
    debug_rows = None
    if debug_csv_path:
        if debug_csv_path.exists():
            debug_rows = load_rows(debug_csv_path)
        else:
            log.warning("debug CSV 파일이 없습니다: %s", debug_csv_path)

    errors, warnings, total = validate(
        rows,
        debug_rows=debug_rows,
        min_success_rate=min_success_rate,
    )

    log.info("검증 완료: total=%d errors=%d warnings=%d", total, errors, warnings)
    if errors > 0:
        return 1
    if strict and warnings > 0:
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="User extraction PoC 검증")
    parser.add_argument("--csv", required=True, help="Step7 결과 CSV 경로")
    parser.add_argument(
        "--debug-csv",
        default="outputs/user_poc/user_face_features_poc_debug.csv",
        help="Step7 디버그 CSV 경로 (없으면 성공률/품질 검증 생략)",
    )
    parser.add_argument("--strict", action="store_true", help="warning도 실패 처리")
    parser.add_argument("--min-success-rate", type=float, default=70.0, help="최소 허용 성공률(%%)")
    args = parser.parse_args()

    raise SystemExit(
        run(
            csv_path=Path(args.csv),
            debug_csv_path=Path(args.debug_csv) if args.debug_csv else None,
            strict=args.strict,
            min_success_rate=float(args.min_success_rate),
        )
    )
