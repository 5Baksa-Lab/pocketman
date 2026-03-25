# Pocketman 프로덕션 개발 플랜

> 작성일: 2026-03-09
> 기준 브랜치: `dev/su`
> 목표: 로컬 프로토타입 → 실제 배포 가능한 프로덕션 서비스

---

## 현재 상태 요약

| 항목 | 상태 | 비고 |
|---|---|---|
| 4-layer 아키텍처 | ✅ 구현 완료 | router→domain→repository→adapter |
| 28D 벡터 파이프라인 | ✅ 구현 완료 | scripts/01~06 |
| MediaPipe CV 추출 | ✅ 구현 완료 | scripts/user_poc/extractor.py |
| Mock 모드 전체 플로우 | ✅ 동작 | USE_MOCK_AI=true |
| 광장 피드 | ✅ 구현 완료 | LIMIT/OFFSET, 반응 카운터 |
| 개발일지 12개 | ✅ 완료 | 전 파트/스테이지 |
| 아키텍처 문서 | ✅ 완료 | docs/ARCHITECTURE.md |
| DB 연결 풀링 | ❌ 미구현 | 요청마다 psycopg2.connect() |
| CORS 제한 | ❌ 미구현 | allow_origins=["*"] |
| 임시파일 누수 | ❌ 버그 | cv_adapter.py os.unlink 위치 |
| Imagen 실제 연동 | ❌ 미완성 | REST endpoint 방식이나 SDK 미확인 |
| Veo 실제 연동 | ❌ 미완성 | 동일 |
| Railway DB 벡터 적재 | ❌ 미실행 | 386개 포켓몬 벡터 없음 |
| Railway 배포 | ❌ 미완료 | |
| Vercel 배포 | ❌ 미완료 | |
| 인증/인가 | ❌ 없음 | Write API 전부 무인증 |
| Rate Limiting | ❌ 없음 | |
| 테스트 | ❌ 없음 | |
| CI/CD | ❌ 없음 | |

---

## Phase 0 — 완료된 작업 (현재까지)

> 코드, 문서 모두 `dev/su` 브랜치에 푸시 완료

- [x] 전체 프로젝트 코드 분석 및 코드 리뷰
- [x] 5박사 원본과 pocketman-dev-su 차이 분석
- [x] 12개 파트별 개발일지 작성 (frontend/backend/mlops/pm-devops 각 3 Stage)
- [x] `docs/ARCHITECTURE.md` 종합 아키텍처 문서 작성
- [x] `docs/common_rule/` — 파트별 AI 컨텍스트 파일 현행화
- [x] `docs/develop_rule/` — 개발 규칙 현행화 (계층명, Stage 목록 등)

---

## Phase 1 — Critical Bug Fix (P0: 배포 전 필수)

> 이 3개가 수정되지 않으면 배포해도 실서비스 불가

### 1-A. cv_adapter.py 임시파일 누수 수정

**문제**: `extractor.extract()` 도중 예외 발생 시 임시파일이 삭제되지 않고 디스크에 남음
**위치**: `backend/app/adapter/cv_adapter.py:83~87`

```python
# 현재 (버그)
with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
    tmp.write(image_bytes)
    tmp_path = tmp.name

result, _ = extractor.extract(tmp_path)  # 여기서 예외 나면
os.unlink(tmp_path)                       # 이 줄 영원히 실행 안 됨

# 수정
with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
    tmp.write(image_bytes)
    tmp_path = tmp.name

try:
    result, _ = extractor.extract(tmp_path)
finally:
    os.unlink(tmp_path)
```

### 1-B. DB 커넥션 풀링 적용

**문제**: 요청마다 `psycopg2.connect()` 신규 연결 → 동시 요청 10개면 DB 연결 10개 생성
**위치**: `backend/app/core/db.py`

`psycopg2.pool.ThreadedConnectionPool` 또는 `psycopg2.pool.SimpleConnectionPool`으로 교체
Pool 크기: min=2, max=10 (Railway 무료 플랜 한계 고려)

### 1-C. CORS 도메인 제한

**문제**: `allow_origins=["*"]` — 어느 도메인에서나 API 호출 가능
**위치**: `backend/app/main.py:25`

```python
# 수정: 환경변수로 관리
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)
```

---

## Phase 2 — 배포 인프라 구축 (P1)

### 2-A. Railway — PostgreSQL + Backend 배포

1. Railway 프로젝트 생성
2. PostgreSQL 17 서비스 추가 + pgvector extension 활성화
3. `database/01_schema.sql` 적용
4. Backend 서비스 배포 (Dockerfile 사용)
5. 환경변수 설정: `DATABASE_URL`, `GEMINI_API_KEY`, `USE_MOCK_AI`, `ALLOWED_ORIGINS`
6. `GET /health` 응답 확인

> **주의**: `backend/Dockerfile`에 `scripts/shared/`와 `scripts/user_poc/` 디렉토리가 반드시 포함되어야 함
> `cv_adapter.py`가 이 경로에 의존함

### 2-B. MLOps 파이프라인 실행 — Railway DB에 포켓몬 벡터 적재

```bash
# .env에 Railway DATABASE_URL 설정 후
python3 scripts/01_fetch_pokeapi.py      # 386종 수집
python3 scripts/02_annotate_gemini_vision.py  # USE_MOCK_AI=true 권장
python3 scripts/03_calc_impression.py
python3 scripts/04_calc_type_affinity.py
python3 scripts/05_build_vectors.py      # DB 적재
python3 scripts/06_validate.py           # 386건 검증
```

> 이 단계 완료 전까지 pgvector 매칭 자체가 동작하지 않음 (핵심 기능 불가)

### 2-C. Vercel — Frontend 배포

1. Vercel 프로젝트 연결 (`frontend/` 디렉토리)
2. 환경변수 설정: `NEXT_PUBLIC_API_BASE_URL=<Railway Backend URL>`
3. 빌드/배포 확인
4. 배포 도메인을 Backend `ALLOWED_ORIGINS`에 추가

---

## Phase 3 — 실 API 연동 완성 (P1)

### 3-A. Imagen 3 실제 연동 확인

**현재 상황**: `generation_adapter.py`가 `IMAGEN_API_URL`로 HTTP POST를 전송하는데, 이 URL이 Google AI Studio의 실제 Imagen 3 엔드포인트와 맞는지 확인 필요.

Google Imagen 3는 Vertex AI SDK 또는 `google-generativeai` SDK를 사용하며 단순 REST endpoint와 다를 수 있음.

확인 항목:
- `IMAGEN_API_URL` 실제 값과 인증 방식 확인
- 응답 포맷이 `{"image_url": "..."}` 형태인지 확인
- 이미지 URL이 영구적인지 또는 만료되는 임시 URL인지 확인

> **이미지 영속성 문제**: Imagen이 반환하는 URL이 임시 URL이라면,
> S3 또는 Cloudflare R2에 저장하는 레이어가 필요함 (3-C 참고)

### 3-B. Veo API 실제 연동 확인

동일하게 `VEO_API_URL` 실제 연동 확인.
Veo는 비동기 Job 방식 — 현재 코드는 단건 요청 후 상태를 별도 폴링하는 구조로 되어 있으나, 실제 Veo API의 Job ID 반환 방식이 맞는지 확인 필요.

### 3-C. 이미지/영상 영속성 저장소 (조건부)

Imagen/Veo API가 만료되는 임시 URL을 반환하는 경우:
- Cloudflare R2 (무료 플랜으로 시작 가능) 또는 AWS S3에 업로드
- `generation_adapter.py`에서 이미지 바이트 다운로드 후 R2에 PUT, 영구 URL을 DB에 저장

> 현재 Mock 모드에서는 `placehold.co` URL을 사용하므로 Mock으로는 문제 없음

---

## Phase 4 — 신뢰성 & 보안 (P2)

### 4-A. Rate Limiting

프레임워크: `slowapi` (FastAPI용 `limits` 래퍼)

```python
# POST /match — 업로드 헤비 엔드포인트
@limiter.limit("10/minute")  # IP당

# POST /creatures/{id}/generate — AI 비용 발생
@limiter.limit("5/minute")

# POST /creatures/{id}/reactions — 어뷰징 방지
@limiter.limit("30/minute")
```

### 4-B. 파일 업로드 입력 검증 강화

현재 `POST /match`에서 파일 타입/크기 검증이 프론트엔드에만 있음.
백엔드에서도 서버사이드 검증 필요:

- 파일 크기: 10MB 이하
- MIME 타입: image/jpeg, image/png, image/webp만 허용
- 파일 내용 검사 (magic bytes): content-type 스푸핑 방지

### 4-C. Write API 인증 (선택적 — 데모 수준이면 생략 가능)

현재 `POST /creatures`, `POST /creatures/{id}/reactions` 등 Write API가 완전 무인증.

옵션 A: 세션 토큰 (간단) — 업로드 완료 시 서버가 세션 ID 발급, 이후 Write API에 포함
옵션 B: 완전 무인증 유지 — 데모/포트폴리오 수준이라면 Rate Limiting만으로 충분

### 4-D. 시크릿 관리 확인

- `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- `GEMINI_API_KEY`가 어디에도 하드코딩되어 있지 않은지 확인
- Railway, Vercel 환경변수 설정 완료 확인

---

## Phase 5 — 테스트 (P2)

### 5-A. Backend 단위 테스트 (핵심 도메인)

```bash
backend/tests/
├── test_match_service.py      # Top-K 매칭 로직
├── test_reasoning_service.py  # rule-based 라벨 생성
├── test_cv_adapter.py         # 28D 벡터 생성 (mock extractor 사용)
└── test_generation_adapter.py # Mock 모드 검증
```

테스트 프레임워크: `pytest` + `unittest.mock`
DB는 mock으로 분리하여 단위 테스트가 실제 DB 없이 실행되도록 구성.

### 5-B. API Integration 테스트

`USE_MOCK_AI=true` + 로컬 Docker DB를 사용한 통합 테스트:

```bash
# 핵심 플로우 검증
POST /api/v1/match           → Top3 포켓몬 반환
POST /api/v1/creatures       → creature 생성
POST /api/v1/creatures/{id}/generate → 이름/이미지/스토리 생성
GET  /api/v1/creatures/public → 광장 피드 반환
```

### 5-C. E2E 수동 테스트 체크리스트

배포 후 아래 시나리오를 3회 연속 성공해야 배포 완료로 인정:

1. 얼굴 사진 업로드 → 매칭 Top3 표시 (10초 이내)
2. 포켓몬 선택 → 크리처 이름/이미지/스토리 생성 완료
3. Veo 폴링 → 영상 표시 (또는 CSS fallback 표시)
4. 광장 공유 → 광장 피드에서 확인
5. 반응(like/wow) 클릭 → 카운터 증가 확인

---

## Phase 6 — 기능 완성 (P3)

### 6-A. KakaoTalk 공유 — 공식 결정 필요

현재 기획에는 있으나 코드에 없음. 두 가지 중 선택:

**옵션 A: 구현**
KakaoTalk JavaScript SDK → `Kakao.Share.sendDefault()` 호출
필요: Kakao Developers 앱 등록, JavaScript 키
작업량: 프론트엔드 1~2일

**옵션 B: Web Share API로 대체**
`navigator.share()` — 모바일에서 OS 기본 공유 시트 사용 (카카오 포함)
작업량: 30분

### 6-B. 크리처 이름 백엔드 저장

현재 Result 화면에서 이름 편집이 가능하지만 저장하지 않음.
`PATCH /api/v1/creatures/{id}` 엔드포인트 추가 필요.

### 6-C. 광장 N+1 문제 해결

`app/plaza/page.tsx`의 `hydrateSummary` 패턴이 크리처 1개당 API 1회 호출하는 구조.
백엔드에서 피드 응답에 반응 요약을 포함하는 방식으로 수정.

---

## Phase 7 — 관측성 & 모니터링 (P3)

### 7-A. 구조화 로깅 완성

현재 `logging.basicConfig`만 설정된 상태. 프로덕션에서는:

```python
# JSON 형태로 로그 출력 (Railway 로그 수집 용이)
{
    "request_id": "uuid",
    "stage": "cv_extract",
    "duration_ms": 234,
    "success": true,
    "error_code": null
}
```

### 7-B. Sentry 에러 모니터링

```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"))
```

무료 플랜으로 에러 알림, 스택 트레이스 수집 가능.

### 7-C. 헬스체크 개선

현재 `GET /health`는 단순 응답만 반환. DB 연결 상태도 포함:

```python
@router.get("/health")
def health():
    db_ok = check_db_connection()
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}
```

---

## Phase 8 — CI/CD (P3)

### 8-A. GitHub Actions 파이프라인

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  backend-test:
    - pytest tests/
    - flake8 backend/ (느슨한 설정)
  frontend-test:
    - npm run lint
    - npm run build
```

### 8-B. 자동 배포

- `main` 브랜치 머지 → Railway 자동 배포 (Railway GitHub 연동)
- `main` 브랜치 머지 → Vercel 자동 배포 (Vercel GitHub 연동)

---

## 전체 로드맵 요약

```
현재 (완료)          Phase 1       Phase 2       Phase 3
코드+문서 완료  →  버그 3개 수정 → 배포 인프라  → 실 API 연동
                  (1~2일)        (2~3일)        (1~3일)

Phase 4       Phase 5       Phase 6       Phase 7/8
보안/신뢰성  →  테스트       →  기능 완성  → 모니터링+CI/CD
(1~2일)        (2~3일)        (1~2일)       (1~2일)
```

### 우선순위 결정 기준

| Phase | 건너뛰면? |
|---|---|
| Phase 1 (버그 3개) | 프로덕션 배포 불가. 반드시 먼저. |
| Phase 2 (배포) | E2E 테스트 불가. 거의 필수. |
| Phase 3 (실 API) | Mock 모드로 데모는 가능. 실서비스엔 필수. |
| Phase 4 (보안) | 어뷰징/보안 취약점. 공개 배포 전 필수. |
| Phase 5 (테스트) | 회귀 위험. 팀 규모가 크면 필수, 소규모면 수동 E2E로 대체 가능. |
| Phase 6 (기능 완성) | 데모 수준에서는 선택적. |
| Phase 7/8 (모니터링/CI) | 장기 운영 필수. 데모만이면 생략 가능. |

---

## 다음 즉시 실행할 작업 (Phase 1)

```
1. backend/app/adapter/cv_adapter.py  — try/finally 수정
2. backend/app/core/db.py             — ThreadedConnectionPool 적용
3. backend/app/main.py                — ALLOWED_ORIGINS 환경변수화
```

세 파일 모두 수정 범위가 10~20줄 이내. Phase 1 완료 후 Phase 2(배포) 착수.
