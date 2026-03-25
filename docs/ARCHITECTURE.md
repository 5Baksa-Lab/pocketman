# Pocketman 시스템 아키텍처 (2026-03-09)

> **기준 디렉토리:** `pocketman-dev-su` (5박사 프로젝트 메인)
> **GitHub:** `https://github.com/5Baksa-Lab/pocketman` — `dev/su` 브랜치

---

## 1. 서비스 개요

**"내 얼굴을 분석해 닮은 포켓몬을 찾고, 나만의 오리지널 크리처를 AI로 생성하는 서비스"**

| 단계 | 설명 |
|------|------|
| 사진 업로드 | 사용자가 얼굴 사진 업로드 |
| 매칭 | MediaPipe로 얼굴 특징 추출 → 28차원 벡터 → pgvector 유사도 검색 → Top-3 포켓몬 |
| 선택 | 사용자가 Top-3 중 1개 선택 |
| 생성 | Gemini Flash(이름/스토리) + Imagen 3(이미지) + Veo(영상) 병렬 생성 |
| 공유 | URL 복사 / Twitter 공유 / 광장(Plaza) 공개 피드 등록 |

---

## 2. 시스템 아키텍처 전체도

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 브라우저                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │             Frontend  (Next.js 15 / localhost:3000)          │   │
│  │                                                              │   │
│  │  [업로드] → [Top-3 선택] → [생성 중] → [결과] → [광장]        │   │
│  │                                                              │   │
│  │  lib/api.ts ──── HTTP ────────────────────────────────────── │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ REST API (JSON)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Backend  (FastAPI / localhost:8000)                │
│                                                                     │
│  Router Layer      /api/v1/                                         │
│  ├─ /health        헬스체크                                          │
│  ├─ /match         POST  이미지 → Top-3 매칭                         │
│  ├─ /creatures     CRUD  크리처 관리                                  │
│  ├─ /creatures/{id}/generate  POST  생성 파이프라인                   │
│  ├─ /veo-jobs      GET   Veo 영상 상태 폴링                           │
│  └─ /creatures/public  GET  광장 피드                                │
│                                                                     │
│  Domain Layer                                                       │
│  ├─ match_service.py        매칭 오케스트레이션                       │
│  ├─ reasoning_service.py    유사 이유 생성                            │
│  ├─ pipeline_service.py     생성 파이프라인                           │
│  ├─ creature_service.py     크리처 비즈니스 로직                      │
│  └─ veo_job_service.py      Veo Job 상태 머신                        │
│                                                                     │
│  Adapter Layer                                                      │
│  ├─ cv_adapter.py           이미지 → 28D 벡터 (MediaPipe)            │
│  └─ generation_adapter.py   Gemini / Imagen / Veo API 연동           │
│                                                                     │
│  Repository Layer                                                   │
│  ├─ pokemon_repository.py   pgvector Top-K 검색                     │
│  ├─ creature_repository.py  크리처 CRUD                              │
│  └─ veo_job_repository.py   Veo Job DB                              │
└──────────┬──────────────────────────┬──────────────────────────────┘
           │ psycopg2                  │ httpx / google-generativeai
           ▼                          ▼
┌──────────────────┐      ┌────────────────────────────────────────┐
│   PostgreSQL 17  │      │         외부 AI API                     │
│   + pgvector     │      │                                        │
│  (Railway DB)    │      │  ├─ Gemini 1.5 Flash  (이름/스토리)    │
│                  │      │  ├─ Imagen 3          (크리처 이미지)   │
│  pokemon_vectors │      │  └─ Veo API           (소개 영상)      │
│  creatures       │      │                                        │
│  reactions       │      └────────────────────────────────────────┘
│  veo_jobs        │
└──────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              MLOps  (1회성 배치 — scripts/)                          │
│                                                                     │
│  01_fetch_pokeapi.py    PokeAPI → pokemon_master (386마리)           │
│  02_annotate_gemini.py  Gemini Vision → pokemon_visual (10D)        │
│  03_calc_impression.py  규칙/Gemini → pokemon_impression (9D)       │
│  04_calc_type.py        타입 룰 → pokemon_type_affinity (8D)        │
│  05_build_vectors.py    통합 → pokemon_vectors (28D, L2 정규화)      │
│  06_validate.py         7종 품질 검증                                │
│                                                                     │
│  scripts/shared/feature_mapping.py  ← Backend cv_adapter가 import  │
│  scripts/user_poc/extractor.py      ← Backend cv_adapter가 import  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 28차원 벡터 구조

```
포켓몬 벡터 (pokemon_vectors)     사용자 벡터 (cv_adapter 실시간 생성)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[0]  eye_size_score              ← MediaPipe 468 랜드마크 기하학 계산
[1]  eye_distance_score
[2]  eye_roundness_score
[3]  eye_tail_score
[4]  face_roundness_score
[5]  face_proportion_score
[6]  feature_size_score
[7]  feature_emphasis_score
[8]  mouth_curve_score
[9]  overall_symmetry
─────────────────────────────────
[10] cute                        ← visual 값에서 규칙 기반 계산
[11] calm                           (shared/feature_mapping.py)
[12] smart
[13] fierce
[14] gentle
[15] lively
[16] innocent
[17] confident
[18] unique
─────────────────────────────────
[19] water_affinity              ← impression 값에서 타입 룰 계산
[20] fire_affinity
[21] grass_affinity
[22] electric_affinity
[23] psychic_affinity
[24] normal_affinity
[25] fighting_affinity
[26] ghost_affinity
─────────────────────────────────
[27] has_glasses                 ← 0.0 or 1.0

전체: L2 정규화 → 코사인 유사도 = 내적
매칭: pgvector IVFFlat 인덱스, ORDER BY feature_vector <=> user_vector LIMIT 3
```

---

## 4. 현재 구현 완료 기능

### ✅ 완료

| 영역 | 기능 |
|------|------|
| **DB 스키마** | 10개 테이블 (pokemon_master, visual, impression, type_affinity, vectors, creatures, veo_jobs, reactions, user_face_features, pokemon_stats) |
| **MLOps 파이프라인** | 8단계 스크립트 (PokeAPI 수집 → Gemini 주석 → 벡터 생성 → 검증) |
| **CV 모듈** | MediaPipe 468 랜드마크 기반 28D 사용자 벡터 생성 |
| **Backend API** | 매칭(/match), 크리처 CRUD, 생성 파이프라인, Veo Job, 광장 피드, 리액션 |
| **Frontend UX** | 업로드 → Top-3 선택 → 생성 → 결과 → URL/Twitter 공유 → 광장 등록 |
| **Mock 모드** | `USE_MOCK_AI=true` 시 AI API 없이 전체 플로우 테스트 가능 |

### ❌ 미완료 (다음 작업)

| 항목 | 심각도 | 위치 |
|------|--------|------|
| `cv_adapter.py` 임시 파일 try/finally 누락 | 높음 | `backend/app/adapter/cv_adapter.py:78` |
| CORS 운영 도메인 값 검증 (`ALLOWED_ORIGINS`) | 중간 | `.env` |
| DB 커넥션 풀 미구현 | 중간 | `backend/app/core/db.py` |
| Rate limiting 없음 | 중간 | 전 라우터 |
| 카카오톡 공유 미구현 | 중간 | `frontend/app/page.tsx` |
| 인증/인가 없음 | 높음 | 전 write API |
| MLOps 데이터 실제 적재 여부 미확인 | 높음 | Railway DB |
| 이름 편집 서버 미반영 | 낮음 | `frontend/app/page.tsx` |

---

## 5. 로컬 테스트 방법

### 사전 준비

```bash
# 1. .env 파일 생성 (저장소 루트)
cp .env.example .env  # 없으면 직접 생성

# .env 내용 (Railway DB)
DATABASE_URL=postgresql://postgres:<password>@<tcp-proxy-host>:<port>/railway
ALLOWED_ORIGINS=http://localhost:3000
GEMINI_API_KEY=your_key_here
IMAGEN_API_URL=your_imagen_endpoint
VEO_API_URL=your_veo_endpoint
USE_MOCK_AI=true          # API 키 없어도 테스트 가능
GEMINI_FLASH_MODEL=gemini-1.5-flash-002
```

### Step 1. Railway DB 스키마 적용

```bash
# 스키마 적용
psql "$DATABASE_URL" -f database/01_schema.sql

# 테이블 생성 확인 (10개)
psql "$DATABASE_URL" -c "\dt"
```

### Step 2. MLOps 데이터 파이프라인 (최초 1회)

```bash
cd scripts
pip install -r requirements.txt

python3 01_fetch_pokeapi.py            # ~30분 (포켓몬 386마리 수집)
python3 02_annotate_gemini_vision.py   # ~2시간 (실제) / ~5분 (USE_MOCK_AI=true)
python3 03_calc_impression.py          # ~10분
python3 04_calc_type_affinity.py       # ~5분
python3 05_build_vectors.py            # ~5분
python3 06_validate.py                 # 검증 (전 항목 PASS 확인)

# 빠른 테스트용 (Mock 모드)
USE_MOCK_AI=true python3 02_annotate_gemini_vision.py
```

### Step 3. Backend 기동

```bash
# 방법 A: Docker Compose (권장)
docker compose up -d backend
# 로그 확인
docker compose logs -f backend

# 방법 B: 로컬 직접 실행
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 헬스체크 확인
curl http://localhost:8000/api/v1/health
# 기대 응답: {"success": true, "data": {"status": "ok", "pokemon_count": 386}}
```

### Step 4. Frontend 기동

```bash
cd frontend

# .env.local 생성
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local

npm install
npm run dev
# → http://localhost:3000 접속
```

### Step 5. E2E 시나리오 테스트

```
1. http://localhost:3000 접속
2. 얼굴이 잘 보이는 정면 사진 업로드 (jpg/png/webp, 10MB 이하)
3. "매칭 시작" 클릭 → 약 2초 후 Top-3 포켓몬 카드 표시
4. 마음에 드는 포켓몬 선택
5. "내 크리처 만들기" 클릭
   → USE_MOCK_AI=true: 즉시 Mock 결과 반환
   → USE_MOCK_AI=false: Imagen/Gemini 실제 호출 (~10-15초)
6. 결과 확인: 크리처 이름 / 스토리 / 이미지
7. URL 복사 또는 광장 등록
8. http://localhost:3000/plaza 에서 공개 피드 확인
```

### API 직접 테스트 (curl)

```bash
# 헬스체크
curl http://localhost:8000/api/v1/health

# 매칭 테스트
curl -X POST http://localhost:8000/api/v1/match \
  -F "file=@/path/to/face.jpg"

# 광장 피드 조회
curl http://localhost:8000/api/v1/creatures/public?limit=10

# Swagger UI (자동 문서)
open http://localhost:8000/docs
```

---

## 6. 다음 작업 우선순위

### 🔴 즉시 처리 (코드 수정)

```
1. cv_adapter.py 임시 파일 try/finally 수정        30분
2. CORS allow_origins 프론트 도메인으로 제한        10분
3. DB 커넥션 풀 (psycopg2.pool) 구현               2시간
```

### 🟠 단기 (1주 이내)

```
4. MLOps 데이터 파이프라인 Railway DB 실제 적재 확인
5. E2E 시나리오 3회 연속 성공 검증
6. Rate limiting 미들웨어 (slowapi)               2-4시간
7. 카카오톡 공유 SDK 연동 결정 및 구현             2-4시간
```

### 🟡 중기 (2주 이내)

```
8. 인증/인가 (최소 익명 세션 or JWT)
9. 이름 편집 서버 반영 (PATCH /creatures/{id})
10. Frontend 컴포넌트 분리 (page.tsx 518줄 → 훅/컴포넌트)
11. 광장 피드 N+1 최적화 (hydrateSummary)
12. Railway 배포 자동화 / Vercel 프론트 배포
```

---

## 7. 디렉토리 구조 요약

```
pocketman-dev-su/
├── backend/                  FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/routers/  HTTP 엔드포인트 (5개)
│   │   ├── domain/          비즈니스 로직 (서비스)
│   │   ├── adapter/         외부 연동 (CV, AI API)
│   │   ├── repository/      DB 쿼리 (SQL)
│   │   └── core/            설정, 스키마, 에러
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                 Next.js 15 프론트엔드
│   ├── app/
│   │   ├── page.tsx         메인 플로우 (업로드→결과)
│   │   └── plaza/page.tsx   광장 피드
│   └── lib/
│       ├── api.ts           API 클라이언트
│       └── types.ts         TypeScript 타입
│
├── scripts/                  MLOps 데이터 파이프라인 (1회성 배치)
│   ├── 01~08_*.py           8단계 스크립트
│   ├── shared/
│   │   └── feature_mapping.py  ← Backend cv_adapter가 공유 사용
│   └── user_poc/
│       └── extractor.py        ← Backend cv_adapter가 공유 사용
│
├── database/
│   └── 01_schema.sql        PostgreSQL + pgvector DDL (10개 테이블)
│
├── docker-compose.yml        DB + Backend 컨테이너
│
└── docs/
    ├── ARCHITECTURE.md       ← 이 파일
    ├── 기획/                  v5 최종 기획안
    ├── development_logs/     파트별 개발일지 (12개 Stage)
    └── develop_rule/         개발 규칙 + 템플릿
```

---

## 8. 핵심 주의사항

> **`scripts/shared/`와 `scripts/user_poc/`는 Backend 컨테이너에도 복사됨**
> `backend/Dockerfile`에서 이 폴더들을 COPY하여 `cv_adapter.py`가 import 가능하게 함.
> 이 두 폴더의 함수 시그니처를 변경하면 **Backend와 MLOps 스크립트 양쪽 동시 수정 필요**.

> **`database/01_schema.sql`이 전체 데이터 계약 원장**
> 테이블명/컬럼명을 변경하면 Backend repository 쿼리, Frontend types.ts, MLOps 스크립트 모두 영향.
