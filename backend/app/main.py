"""
Pokéman FastAPI 앱 진입점
기획안 v5 — Router-Service-Repository-Adapter 레이어 구조
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import creatures, generation, health, match, veo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Pokéman API",
    description="내 얼굴과 닮은 포켓몬을 찾아주는 CV 벡터 유사도 매칭 서비스",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중 전체 허용, 배포 시 프론트 도메인으로 제한
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["헬스체크"])
app.include_router(match.router,  prefix="/api/v1", tags=["매칭"])
app.include_router(creatures.router, prefix="/api/v1", tags=["크리처"])
app.include_router(veo.router, prefix="/api/v1", tags=["Veo Jobs"])
app.include_router(generation.router, prefix="/api/v1", tags=["생성 파이프라인"])


@app.get("/")
def root():
    return {"message": "Pokéman API is running. Visit /docs for API documentation."}
