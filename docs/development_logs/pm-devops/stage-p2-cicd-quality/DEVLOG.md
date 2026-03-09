# Stage 개발일지

## 0) 기본 정보
- 파트: `pm-devops`
- Stage: `p2-cicd-quality`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 파트 간 의존성(데이터/API/런타임) 공식 문서화
  - 통합 실행 가이드 작성
  - CI/CD 자동화 목표 상태 기록
- 이번 Stage에서 포함한 범위:
  - 파트 간 의존성 매트릭스 문서화
  - 환경변수 키셋 최종 정리
  - 런타임 기동 순서 확립
- 제외한 범위:
  - CI/CD 파이프라인 실제 구축 (미완 — 기술부채)
  - Railway/Vercel 배포 자동화 (미완)

## 2) 파트 간 의존성 매트릭스

| 공급 파트 | 산출물 | 소비 파트 | 결합 지점 |
|---|---|---|---|
| MLOps (M1) | `pokemon_master`, `pokemon_stats`, `pokemon_visual` | Backend (B2) | `pokemon_repository.py` SQL |
| MLOps (M2) | `pokemon_impression`, `pokemon_type_affinity`, `pokemon_vectors` | Backend (B2) | pgvector 검색 |
| MLOps (M2) | `scripts/shared/feature_mapping.py` | Backend (M3/B2) | `cv_adapter.py` import |
| MLOps (M3) | `scripts/user_poc/` 패키지 | Backend (B2) | `cv_adapter.py` → `extractor.py` |
| Backend (B1~B3) | `/api/v1/*` REST API | Frontend | `frontend/lib/api.ts` |
| Frontend | 이미지 업로드 + 사용자 액션 | Backend | POST /match, POST /creatures |
| PM/DevOps (P1) | `database/01_schema.sql`, `docker-compose.yml` | 전 파트 | 스키마 + 컨테이너 기동 |

## 3) 런타임 기동 순서

```bash
# 1. DB 기동
docker compose up -d db

# 2. 스키마 적용
docker exec -i pocketman-db psql -U pocketman -d pocketman < database/01_schema.sql

# 3. MLOps 파이프라인 (최초 1회)
cd scripts && pip install -r requirements.txt
python3 01_fetch_pokeapi.py && python3 02_annotate_gemini_vision.py
python3 03_calc_impression.py && python3 04_calc_type_affinity.py
python3 05_build_vectors.py && python3 06_validate.py

# 4. Backend 기동
docker compose up -d backend

# 5. Frontend 기동
cd frontend && npm install && npm run dev
```

## 4) 환경변수 키셋

| 키 | 파트 | 필수 | 기본값 |
|---|---|---|---|
| `DATABASE_URL` | Backend, MLOps | 필수 | 없음 |
| `GEMINI_API_KEY` | Backend, MLOps | 필수 | 없음 |
| `GEMINI_FLASH_MODEL` | Backend | 선택 | `gemini-1.5-flash-002` |
| `IMAGEN_API_URL` | Backend | Real 필수 | 없음 |
| `VEO_API_URL` | Backend | Real 필수 | 없음 |
| `USE_MOCK_AI` | Backend | 선택 | `false` |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | 선택 | `http://localhost:8000/api/v1` |

## 5) 통합 리스크 요약

| 리스크 | 심각도 | 대응 |
|---|---|---|
| CORS `allow_origins=["*"]` | 높음 | 배포 전 프론트 도메인 제한 |
| 인증/인가 없음 | 높음 | JWT 또는 세션 도입 |
| DB 커넥션 풀 없음 | 중간 | ThreadedConnectionPool |
| Rate limiting 없음 | 중간 | slowapi 미들웨어 |
| cv_adapter 임시 파일 누수 | 중간 | try/finally 수정 |
| 카카오톡 공유 미구현 | 중간 | SDK 앱 등록 후 연동 |
| hydrateSummary N+1 | 낮음 | Promise.all 또는 API 변경 |
| 개발일지 사후 작성 | 낮음 | 향후 실시간 작성 |

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: CI/CD 미구축 현황, 리스크 심각도 분류

## 7) 완료 체크
- [x] 파트 간 의존성 매트릭스 문서화 완료
- [x] 런타임 기동 순서 문서화 완료
- [x] 환경변수 키셋 정리 완료
- [ ] CI/CD 파이프라인 구축 (미완)
- [x] 개발일지 파일 생성: `docs/development_logs/pm-devops/stage-p2-cicd-quality/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
