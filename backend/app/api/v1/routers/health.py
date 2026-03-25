"""
GET /api/v1/health — 서버/DB 상태 확인
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.repository.pokemon_repository import get_db_stats

router = APIRouter()


@router.get("/health")
def health():
    try:
        stats = get_db_stats()
        return {
            "status": "ok",
            "db": "connected",
            "pokemon_count": stats["pokemon_count"],
            "vector_count": stats["vector_count"],
        }
    except Exception as e:
        return JSONResponse(status_code=200, content={
            "status": "ok",
            "db": "disconnected",
            "detail": str(e),
        })
