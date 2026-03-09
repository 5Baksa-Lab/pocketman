# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b2-match-generate`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 실제 CV 벡터 생성 → pgvector Top-3 검색 → 매칭 결과 반환 구현
  - 크리처 생성 파이프라인 (이름/스토리/이미지) API 구현
- 이번 Stage에서 포함한 범위:
  - `routers/match.py`, `routers/creatures.py`, `routers/generation.py`
  - `domain/matching/match_service.py`, `reasoning_service.py`
  - `domain/creatures/creature_service.py`
  - `domain/generation/pipeline_service.py`
  - `repository/pokemon_repository.py`, `creature_repository.py`
  - `adapter/cv_adapter.py`, `adapter/generation_adapter.py`

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **매칭 흐름을 match_service.py 단일 오케스트레이터로 집중**
  ```python
  user_vector, raw_features = build_user_vector(image_bytes)
  pokemon_rows = search_top_k(user_vector, k=TOP_K)
  reasons = generate_reasons(user_visual, user_impression, row)
  return MatchResponse(top3=top3, user_vector=user_vector.tolist())
  ```
- 결정 2: **근거 생성을 규칙 기반 라벨 비교로 구현**
  - `_VISUAL_LABELS`, `_IMPRESSION_LABELS` 딕셔너리 매핑
  - 사용자 값과 포켓몬 값의 차이가 작은 차원 top-3 선택
- 결정 3: **생성 파이프라인을 ThreadPoolExecutor 병렬 실행**
  - 이름/스토리(Gemini) + 이미지(Imagen) 병렬
- 결정 4: **실패 시 fallback 허용으로 서비스 가용성 우선**

### 2.2 핵심 로직 설명
- `/api/v1/match` 에러 분기:
  - FaceNotDetectedError → 422 FACE_NOT_DETECTED
  - MultipleFacesError → 422 MULTIPLE_FACES
  - LowQualityError → 422 LOW_QUALITY
  - 매칭 결과 없음 → 404 NO_MATCH_FOUND
- pgvector Top-K 검색 SQL (pokemon_repository.py):
  ```sql
  SELECT pm.*, pv.*, pi.*,
    1 - (pf.feature_vector <=> %s::vector) AS similarity
  FROM pokemon_vectors pf
  JOIN pokemon_master pm USING (pokemon_id)
  JOIN pokemon_visual pv USING (pokemon_id)
  JOIN pokemon_impression pi USING (pokemon_id)
  ORDER BY pf.feature_vector <=> %s::vector
  LIMIT %s
  ```
- Imagen/Gemini 어댑터: Mock(즉시 반환) + Real(httpx 호출, 재시도 2회, 지수 백오프 0.8×2^idx)

### 2.3 변경 파일 목록
- `routers/match.py`, `routers/creatures.py`, `routers/generation.py`
- `domain/matching/match_service.py` (46줄), `reasoning_service.py` (86줄)
- `domain/creatures/creature_service.py`, `domain/generation/pipeline_service.py`
- `repository/pokemon_repository.py`, `repository/creature_repository.py`
- `adapter/cv_adapter.py` (146줄), `adapter/generation_adapter.py`

## 3) 테스트/검증
- `python3 -m compileall -q backend/app/` → exit=0
- 라우터 경로 ↔ 프론트 api.ts 호출 경로 정합성 수동 확인
- pgvector SQL 컬럼명 ↔ 01_schema.sql 일치 확인
- cv_adapter 벡터 차원 순서 ↔ M2 05_build_vectors.py 일치 확인

## 4) 이슈/리스크
- **버그: cv_adapter.py 임시 파일 try/finally 없음** (M3에서 인계받은 미수정 버그)
- `except Exception as e` 광범위 사용 — 스택 트레이스 없이 에러 삼킴
- DB 커넥션 풀 미구현
- 인증 없음

## 5) 다음 Stage 인수인계 (B3)
- Veo Job API, 광장 피드 API, 리액션 API 구현
- `cv_adapter.py` 임시 파일 try/finally 수정 (P3 이전 반드시 처리)
- Rate limiting 미들웨어 추가

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 임시 파일 누수 이슈 구체화, 커넥션 풀 미구현 리스크 추가

## 7) 완료 체크
- [x] POST /api/v1/match 구현 완료
- [x] pgvector Top-K 검색 구현 완료
- [x] 근거 생성 서비스 구현 완료
- [x] 크리처 CRUD API 구현 완료
- [x] 생성 파이프라인 구현 완료
- [x] Gemini/Imagen 어댑터 구현 완료
- [ ] cv_adapter.py 임시 파일 try/finally 수정 (미완)
- [ ] DB 커넥션 풀 (미완)
- [x] 개발일지 파일 생성: `docs/development_logs/backend/stage-b2-match-generate/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
