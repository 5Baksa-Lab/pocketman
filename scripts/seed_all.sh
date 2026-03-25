#!/usr/bin/env bash
# =============================================================================
# Pokéman 포켓몬 DB 전체 시드 스크립트
# 사용법: bash scripts/seed_all.sh
#
# 전제 조건:
#   1. docker-compose up -d db  (PostgreSQL + pgvector 실행 중)
#   2. .venv 활성화 상태
#   3. .env에 DATABASE_URL 설정 완료
#
# 실행 순서:
#   Step 1: PokeAPI 배치 수집 (386마리, ~10분)
#   Step 2: Gemini Vision 시각 특징 (Mock 모드: ~30초)
#   Step 3: 인상 점수 계산 (Mock 모드: ~30초)
#   Step 4: 타입 친화도 계산 (~10초)
#   Step 5: 28차원 벡터 생성 (~10초)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  Pokéman 포켓몬 DB 시드 시작"
echo "=============================================="

# Step 1: PokeAPI 배치 수집
echo ""
echo "[Step 1/5] PokeAPI 배치 수집 (386마리)..."
echo "  ※ 약 10~15분 소요 (API rate limit 대기 포함)"
python 01_fetch_pokeapi.py
echo "[Step 1/5] 완료!"

# Step 2: 시각 특징 주석 (Mock 모드)
echo ""
echo "[Step 2/5] 시각 특징 주석 (USE_MOCK_AI=${USE_MOCK_AI:-true})..."
USE_MOCK_AI="${USE_MOCK_AI:-true}" python 02_annotate_gemini_vision.py
echo "[Step 2/5] 완료!"

# Step 3: 인상 점수 계산
echo ""
echo "[Step 3/5] 인상 점수 계산..."
USE_MOCK_AI="${USE_MOCK_AI:-true}" python 03_calc_impression.py
echo "[Step 3/5] 완료!"

# Step 4: 타입 친화도 계산
echo ""
echo "[Step 4/5] 타입 친화도 계산..."
python 04_calc_type_affinity.py
echo "[Step 4/5] 완료!"

# Step 5: 28차원 벡터 생성
echo ""
echo "[Step 5/5] 28차원 벡터 생성 + pgvector 저장..."
python 05_build_vectors.py
echo "[Step 5/5] 완료!"

echo ""
echo "=============================================="
echo "  전체 시드 완료!"
echo "  검증: python 06_validate.py"
echo "=============================================="
