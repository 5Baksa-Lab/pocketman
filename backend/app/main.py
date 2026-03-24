"""
Pokéman FastAPI 앱 진입점
기획안 v5 — Router-Service-Repository-Adapter 레이어 구조
"""
import logging
import os
import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import auth, creatures, generation, health, match, users, veo
from app.api.v1.sockets.plaza_socket import sio
from app.core.config import ALLOWED_ORIGINS, GENERATED_FILES_DIR

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
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["헬스체크"])
app.include_router(match.router,  prefix="/api/v1", tags=["매칭"])
app.include_router(creatures.router, prefix="/api/v1", tags=["크리처"])
app.include_router(veo.router, prefix="/api/v1", tags=["Veo Jobs"])
app.include_router(generation.router, prefix="/api/v1", tags=["생성 파이프라인"])
app.include_router(auth.router,    prefix="/api/v1", tags=["인증"])
app.include_router(users.router,   prefix="/api/v1", tags=["사용자"])


# 생성 이미지/영상 정적 파일 서빙
os.makedirs(GENERATED_FILES_DIR, exist_ok=True)
app.mount("/static/generated", StaticFiles(directory=GENERATED_FILES_DIR), name="generated")


@app.get("/")
def root():
    return {"message": "Pokéman API is running. Visit /docs for API documentation."}


# Socket.io + FastAPI 결합 ASGI 앱 (uvicorn app.main:combined_app)
combined_app = socketio.ASGIApp(sio, other_asgi_app=app)
