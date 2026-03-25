"""
POST /api/v1/match — 얼굴 사진 업로드 → Top-3 포켓몬 매칭
"""
import time
import logging
import uuid

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from app.domain.matching.match_service import match_pokemon
from app.core.errors import PocketmanError

log = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/match")
async def match(file: UploadFile = File(...)):
    """
    얼굴 사진 업로드 → Top-3 포켓몬 + 근거 반환

    - Content-Type: multipart/form-data
    - 파일 필드명: file
    - 지원 포맷: JPEG, PNG, WebP (최대 10MB)
    """
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    # 파일 형식 검증
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return JSONResponse(status_code=415, content={
            "success": False,
            "error_code": "UNSUPPORTED_MEDIA_TYPE",
            "message": f"지원하지 않는 파일 형식입니다. (JPEG/PNG/WebP만 허용)",
        })

    image_bytes = await file.read()

    # 파일 크기 검증
    if len(image_bytes) > MAX_FILE_SIZE:
        return JSONResponse(status_code=413, content={
            "success": False,
            "error_code": "FILE_TOO_LARGE",
            "message": "파일 크기가 10MB를 초과합니다.",
        })

    try:
        result = match_pokemon(image_bytes)
        duration_ms = int((time.time() - start) * 1000)

        if not result.top3:
            log.warning(f"[{request_id}] match 결과 없음 | duration={duration_ms}ms")
            return JSONResponse(status_code=404, content={
                "success": False,
                "error_code": "NO_MATCH_FOUND",
                "message": "유사한 포켓몬을 찾지 못했습니다.",
            })

        log.info(
            f"[{request_id}] match 성공 | duration={duration_ms}ms | "
            f"top1={result.top3[0].name_kr}({result.top3[0].similarity:.3f})"
        )

        return {
            "success": True,
            "request_id": request_id,
            "duration_ms": duration_ms,
            "data": result.model_dump(),
        }

    except PocketmanError as e:
        duration_ms = int((time.time() - start) * 1000)
        log.warning(f"[{request_id}] match 실패 | duration={duration_ms}ms | {e.detail}")
        return JSONResponse(status_code=e.status_code, content={
            "success": False,
            **e.detail,
        })

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        log.error(f"[{request_id}] match 오류 | duration={duration_ms}ms | {e}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        })
