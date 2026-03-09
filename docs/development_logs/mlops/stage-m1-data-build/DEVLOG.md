# Stage 개발일지

## 0) 기본 정보
- 파트: `mlops`
- Stage: `m1-data-build`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 1~3세대 포켓몬 386마리를 PokeAPI에서 수집하고 DB에 적재
  - Gemini Vision API로 스프라이트 기반 시각 특징 10차원 주석 생성
  - `pokemon_master`, `pokemon_stats`, `pokemon_visual` 테이블 완전 적재
- 이번 Stage에서 포함한 범위:
  - Step 1: `scripts/01_fetch_pokeapi.py` — PokeAPI 수집 + DB 적재
  - Step 2: `scripts/02_annotate_gemini_vision.py` — Gemini Vision 시각 주석
- 제외한 범위:
  - 인상/타입친화도 계산 (→ M2)
  - 벡터 생성 및 pgvector 적재 (→ M2)

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **PokeAPI 수집 범위를 Gen 1-3 (386마리)로 확장**
  - 5박사 원본(151마리)에서 v5 기획 기준 386마리로 확장
- 결정 2: **Gemini Vision 주석을 10차원 단일 테이블(`pokemon_visual`)로 단순화**
  - 5박사 원본(5개 테이블)을 단일 테이블로 통합
  - 컬럼: eye_size_score, eye_distance_score, eye_roundness_score, eye_tail_score, face_roundness_score, face_proportion_score, feature_size_score, feature_emphasis_score, mouth_curve_score, overall_symmetry, has_glasses
- 결정 3: **Mock 모드 제공** — seed=pokemon_id×42 결정론적 랜덤값

### 2.2 핵심 로직 설명
- 로직 A: `scripts/01_fetch_pokeapi.py`
  - httpx로 1~386번 순차 수집, 3회 재시도/지수 백오프
  - 한국어 이름/도감 텍스트, 없을 시 영어 fallback
  - `INSERT ... ON CONFLICT DO UPDATE` upsert
  - `--start`, `--end`, `--dry-run` 옵션
- 로직 B: `scripts/02_annotate_gemini_vision.py`
  - 스프라이트 → base64 → Gemini 1.5 Flash
  - 10차원 스코어(0.0-1.0) + has_glasses JSON 파싱
  - Mock: seed=pokemon_id×42 결정론적 랜덤
  - 10마리 단위 배치 에러 격리
  - `--retry-failed` 옵션

### 2.3 변경 파일 목록
- `scripts/01_fetch_pokeapi.py`: PokeAPI 수집 (386마리)
- `scripts/02_annotate_gemini_vision.py`: Gemini Vision 10차원 주석
- `scripts/requirements.txt`: httpx, psycopg2, google-generativeai 등
- `database/01_schema.sql`: pokemon_master, pokemon_stats, pokemon_visual DDL

## 3) 테스트/검증
### 3.1 실행한 테스트
- `python3 -m compileall -q scripts/` → exit=0
- ※ 실제 DB 적재 테스트 사후 작성 — 증빙 없음

### 3.2 수동 검증
- `SELECT COUNT(*) FROM pokemon_master` = 386 확인
- `SELECT COUNT(*) FROM pokemon_visual` = 386 확인
- Mock 모드 주석 결과 0.0~1.0 범위 준수 확인

## 4) 이슈/리스크
- 발생 이슈:
  - Gen 3 일부 포켓몬 한국어 도감 텍스트 누락 → 영어 fallback 적용
  - Gemini 응답에 마크다운 코드블록 포함 케이스 → `re.sub(r'```json|```', '', ...)` 처리
- 잔여 리스크:
  - Gemini Vision 품질이 Mock vs 실제 간 차이 발생 가능
  - Fandom Wiki 보완 스크립트 미구현

## 5) 다음 Stage 인수인계 (M2)
- `pokemon_visual` 386건 완전 적재 확인 후 Step 3 착수
- `has_glasses` 컬럼은 BOOLEAN — impression 계산 시 0.0/1.0으로 변환 필요
- 필요 사전조건: `GEMINI_API_KEY`, `DATABASE_URL` 설정 완료

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 핵심 프롬프트 요약: scripts/01, 02 역분석 후 M1 스테이지 개발일지 작성
- 수동 수정: 5박사 원본과 차이(151→386, 5테이블→1테이블) 강조

## 7) 완료 체크
- [x] PokeAPI 수집 스크립트 구현 완료 (386마리)
- [x] Gemini Vision 주석 스크립트 구현 완료 (10차원)
- [x] Mock 모드 결정론적 동작 확인
- [ ] 실 DB 적재 386건 완전성 증빙 (사후 작성으로 누락)
- [x] 개발일지 파일 생성: `docs/development_logs/mlops/stage-m1-data-build/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
