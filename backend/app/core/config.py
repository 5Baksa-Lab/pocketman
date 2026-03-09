"""
앱 설정 (환경변수 기반)
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values or [default]


DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
ALLOWED_ORIGINS: list[str] = _parse_csv_env("ALLOWED_ORIGINS", "http://localhost:3000")
USE_MOCK_AI: bool = os.environ.get("USE_MOCK_AI", "false").lower() == "true"
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
GEMINI_FLASH_MODEL: str = os.environ.get("GEMINI_FLASH_MODEL", "gemini-2.0-flash")
IMAGEN_API_URL: str = os.environ.get("IMAGEN_API_URL", "")
VEO_API_URL: str = os.environ.get("VEO_API_URL", "")
AI_REQUEST_TIMEOUT_SEC: int = int(os.environ.get("AI_REQUEST_TIMEOUT_SEC", "30"))
AI_MAX_RETRIES: int = int(os.environ.get("AI_MAX_RETRIES", "2"))
AI_RETRY_BASE_DELAY_SEC: float = float(os.environ.get("AI_RETRY_BASE_DELAY_SEC", "0.8"))
DB_POOL_MIN_CONN: int = int(os.environ.get("DB_POOL_MIN_CONN", "2"))
DB_POOL_MAX_CONN: int = int(os.environ.get("DB_POOL_MAX_CONN", "10"))

# 매칭 설정
TOP_K: int = 3
VECTOR_DIM: int = 28
