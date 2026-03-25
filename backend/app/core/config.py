"""
앱 설정 (환경변수 기반)
"""
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from dotenv import load_dotenv

_log = logging.getLogger(__name__)

load_dotenv()

# 프로젝트 루트 경로 (backend/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values or [default]


def _expand_loopback_origins(origins: list[str]) -> list[str]:
    expanded: list[str] = []

    for origin in origins:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        variants = [origin]

        if hostname in {"localhost", "127.0.0.1"}:
            for alt_host in ("localhost", "127.0.0.1"):
                netloc = alt_host
                if parsed.port:
                    netloc += f":{parsed.port}"
                variants.append(
                    urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
                )

        for candidate in variants:
            if candidate not in expanded:
                expanded.append(candidate)

    return expanded


DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
ALLOWED_ORIGINS: list[str] = _expand_loopback_origins(
    _parse_csv_env("ALLOWED_ORIGINS", "http://localhost:3000")
)
USE_MOCK_AI: bool = os.environ.get("USE_MOCK_AI", "false").lower() == "true"
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL: str = os.environ.get("GEMINI_FLASH_MODEL", "gemini-2.0-flash")
IMAGEN_MODEL: str = os.environ.get("IMAGEN_MODEL", "imagen-3.0-generate-002")
VEO_MODEL: str = os.environ.get("VEO_MODEL", "veo-2.0-generate-001")
AI_REQUEST_TIMEOUT_SEC: int = int(os.environ.get("AI_REQUEST_TIMEOUT_SEC", "30"))
AI_MAX_RETRIES: int = int(os.environ.get("AI_MAX_RETRIES", "2"))
AI_RETRY_BASE_DELAY_SEC: float = float(os.environ.get("AI_RETRY_BASE_DELAY_SEC", "0.8"))
DB_POOL_MIN_CONN: int = int(os.environ.get("DB_POOL_MIN_CONN", "2"))
DB_POOL_MAX_CONN: int = int(os.environ.get("DB_POOL_MAX_CONN", "10"))

# 생성 이미지/영상 저장 경로
GENERATED_FILES_DIR: str = os.environ.get(
    "GENERATED_FILES_DIR",
    str(_BACKEND_ROOT / "static" / "generated"),
)
# 외부 접근 가능한 API base URL (정적 파일 URL 생성에 사용)
API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:8000")

# 매칭 설정
TOP_K: int = 3
VECTOR_DIM: int = 28

# Auth 설정
_JWT_SECRET_KEY_RAW: str = os.environ.get("JWT_SECRET_KEY", "")
if not _JWT_SECRET_KEY_RAW:
    raise RuntimeError(
        "JWT_SECRET_KEY 환경변수가 설정되지 않았습니다. "
        ".env 또는 Railway 환경변수에 JWT_SECRET_KEY를 추가해주세요."
    )
JWT_SECRET_KEY: str = _JWT_SECRET_KEY_RAW
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 24
