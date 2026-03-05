# Pokéman 프로젝트 MLOps 파이프라인 설계서

**작성자:** 시니어 MLOps 엔지니어
**작성일:** 2026년 3월 5일
**버전:** v1.0
**대상 독자:** 5박사연구소 전체 팀원

---

## 0. 설계 원칙

본 설계서는 3주라는 제한된 기간과 4인 팀 구성을 전제로, **"동작하는 MVP를 가장 빠르게 배포하는 것"** 을 최우선 목표로 한다.

- **Simple First:** 처음부터 복잡한 구조를 만들지 않는다. 필요해지면 확장한다.
- **API-First:** 팀 간 블로킹을 없애기 위해 인터페이스를 먼저 확정한다.
- **Fail Fast:** 실패 케이스를 파이프라인 앞단에서 조기 차단한다.
- **Observable:** 무엇이 얼마나 걸리는지 항상 측정 가능해야 한다.

---

## 1. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                          사용자 (브라우저 / 모바일)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js / Vercel)                   │
│  - 사진 업로드 UI                                                │
│  - 로딩 애니메이션 ("크리처 DNA 조합 중...")                      │
│  - 결과 카드 렌더링 (캐릭터 이미지 + 설명 + 스토리)               │
│  - 공유 / 저장 기능                                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API (JSON + multipart)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI / Docker)                    │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────────┐ │
│  │  1. 전처리   │──▶│ 2. CV 추출   │──▶│  3. 속성 매핑       │ │
│  │  (OpenCV)    │   │ (MediaPipe)  │   │  (Rule Engine)      │ │
│  └──────────────┘   └──────────────┘   └──────────┬──────────┘ │
│                                                    │            │
│                              ┌─────────────────────┤            │
│                              │                     │            │
│                    ┌─────────▼──────┐   ┌──────────▼─────────┐ │
│                    │ 4. 이미지 생성 │   │  5. 스토리 생성    │ │
│                    │ (GenAI API)    │   │  (LLM API)         │ │
│                    └────────────────┘   └────────────────────┘ │
│                              │                     │            │
│                              └─────────┬───────────┘            │
│                                        │                         │
│                              ┌─────────▼──────────┐             │
│                              │   6. 결과 조합 &   │             │
│                              │   스토리지 저장    │             │
│                              └────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                   ▼
     ┌────────────────┐ ┌─────────────┐  ┌──────────────────┐
     │ Object Storage │ │  로그/모니터 │  │  외부 API        │
     │ (S3 / R2)      │ │  (Sentry)   │  │  (OpenAI / SD)   │
     └────────────────┘ └─────────────┘  └──────────────────┘
```

---

## 2. CV 파이프라인 상세 설계

### 2-1. 이미지 전처리 (Preprocessing)

```
입력 이미지
    │
    ├─ [검증] 포맷 확인 → jpg / png / webp만 허용
    ├─ [검증] 파일 크기 → 최대 10MB 제한
    ├─ [변환] 리사이즈 → 최대 1280px 단변 기준 (비율 유지)
    ├─ [변환] 색공간 → BGR → RGB 변환
    ├─ [검증] 블러 감지 → Laplacian variance < 50 이면 경고
    └─ [출력] 정규화된 numpy array
```

**주요 실패 케이스 처리:**

| 실패 케이스 | 감지 방법 | 반환 에러 코드 |
|------------|----------|--------------|
| 얼굴 미검출 | MediaPipe confidence < 0.7 | `FACE_NOT_DETECTED` |
| 다중 얼굴 | 검출된 face 수 > 1 | `MULTIPLE_FACES` |
| 저해상도 | 얼굴 bbox < 80x80px | `FACE_TOO_SMALL` |
| 측면 얼굴 | 좌우 랜드마크 비대칭도 > 0.4 | `SIDE_FACE` |
| 저조도 | 이미지 평균 밝기 < 40 | `LOW_BRIGHTNESS` |

### 2-2. 특징 추출 (Feature Extraction)

MediaPipe Face Mesh 468개 랜드마크를 기반으로 아래 7가지 핵심 특징값을 도출한다.

```python
# 추출 특징 목록 (feature_vector 구조)
{
    "eye_distance_ratio": float,   # 눈 사이 거리 / 얼굴 너비 (0.0 ~ 1.0)
    "face_shape_ratio": float,     # 얼굴 세로/가로 비율 (갸름 vs 둥글)
    "eye_size_ratio": float,       # 눈 높이 / 눈 너비 (크기)
    "mouth_width_ratio": float,    # 입 너비 / 얼굴 너비
    "nose_width_ratio": float,     # 코 너비 / 얼굴 너비
    "has_glasses": bool,           # 안경 착용 여부 (눈 주변 직선 패턴 감지)
    "eyebrow_angle": float,        # 눈썹 기울기 (인상 분위기 추정)
}
```

### 2-3. 속성 매핑 (Rule Engine)

추출된 특징값을 캐릭터 속성으로 변환하는 규칙 테이블.
**이 테이블은 1주차 Day 2까지 팀 전체 합의 하에 확정되어야 한다.**

```python
# 매핑 규칙 예시 (매핑 테이블 v1.0)
CHARACTER_MAPPING = {
    "type": {
        # eye_distance_ratio 기준
        "wide_eyes":   {"condition": "> 0.45", "value": "수생형"},
        "narrow_eyes": {"condition": "< 0.35", "value": "조류형"},
        "default":                              "포유형",
    },
    "element": {
        # has_glasses
        True:  "지능/물 속성",
        False: "자연/불 속성",
    },
    "mood": {
        # eyebrow_angle 기준
        "sharp":  {"condition": "> 15deg",  "value": "날카로운"},
        "gentle": {"condition": "< -5deg",  "value": "온화한"},
        "default":                           "중립적인",
    },
    "face_base": {
        # face_shape_ratio 기준
        "long":   {"condition": "> 1.4", "value": "갸름한 얼굴형 크리처"},
        "round":  {"condition": "< 1.1", "value": "둥근 얼굴형 크리처"},
        "default":                        "표준형 크리처",
    },
}
```

---

## 3. 모델 서빙 설계

### 3-1. 이미지 생성 (GenAI)

**전략:** 외부 API(DALL-E 3 또는 Stable Diffusion API)를 우선 사용하고, 이후 자체 서빙으로 전환 여부 결정.

```
캐릭터 속성
    │
    ▼
프롬프트 빌더
    │   예시:
    │   "original creature character, {수생형} base, {물 속성} element,
    │    {온화한} expression, {둥근 얼굴형}, game illustration style,
    │    full body, clean background, high quality"
    │
    ▼
GenAI API 호출 (비동기)
    │
    ├─ 성공 → 이미지 URL 수신 → S3 업로드
    └─ 실패 → 재시도 1회 → fallback 이미지 반환
```

**Negative Prompt (일관성 확보용):**
```
"realistic photo, human face, anime, chibi, low quality,
 blurry, watermark, text, existing IP character"
```

### 3-2. 스토리 생성 (LLM)

```
캐릭터 속성
    │
    ▼
LLM 프롬프트 (System + User)
    │
    │  System: "당신은 포켓몬 세계관의 크리처 도감 작가입니다.
    │            주어진 속성을 바탕으로 50자 이내의 간결한 소개 문구를 작성합니다."
    │
    │  User:   "타입: 수생형, 속성: 물, 분위기: 온화한, 외형: 둥근 얼굴형"
    │
    ▼
LLM API 호출 (Claude or GPT-4o-mini)
    │
    └─ 결과: "잔잔한 호수의 수호자. 둥근 눈망울로 상대의 마음을 읽는 감지형 크리처."
```

### 3-3. 병렬 처리 구조

이미지 생성과 스토리 생성은 **독립적**이므로 동시 실행한다.

```python
# FastAPI 내부 처리 흐름 (의사코드)
async def generate_result(feature_vector: dict):
    character_attrs = rule_engine.map(feature_vector)   # 동기 (빠름)

    image_task  = asyncio.create_task(generate_image(character_attrs))
    story_task  = asyncio.create_task(generate_story(character_attrs))

    image_url, story = await asyncio.gather(image_task, story_task)

    return {
        "character": character_attrs,
        "image_url": image_url,
        "story": story,
    }
```

**목표 응답 시간:**

| 단계 | 예상 소요 시간 |
|------|--------------|
| 전처리 + 특징 추출 | ~1초 |
| 이미지 생성 (병렬) | ~10~20초 |
| 스토리 생성 (병렬) | ~2~3초 |
| **전체 (병렬 기준)** | **~12~22초** |

---

## 4. 인프라 및 배포 설계

### 4-1. 환경 구성

```
┌──────────────────────────────────────────────┐
│               개발 환경 (Local)               │
│  - Docker Compose로 Frontend + Backend 동시 구동│
│  - .env.local 파일로 API Key 관리             │
│  - Mock API로 프론트 독립 개발 지원           │
└──────────────────────────────────────────────┘
                    │ Git Push (main)
                    ▼
┌──────────────────────────────────────────────┐
│            CI/CD (GitHub Actions)            │
│  - PR: pytest 자동 실행 (단위 테스트)         │
│  - main 머지: 자동 빌드 + 배포               │
│  - 환경변수: GitHub Secrets 관리             │
└──────────────────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        ▼                      ▼
┌───────────────┐     ┌────────────────┐
│  Vercel       │     │  Railway / EC2 │
│  (Frontend)   │     │  (Backend)     │
│  Next.js      │     │  Docker 컨테이너│
│  자동 배포    │     │  FastAPI       │
└───────────────┘     └────────────────┘
```

### 4-2. Docker 구성

```yaml
# docker-compose.yml (로컬 개발용)
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env.local
    volumes:
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file:
      - .env.local
    depends_on:
      - backend
```

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# OpenCV 의존 라이브러리
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4-3. 브랜치 전략

```
main          ─── 배포 브랜치 (항상 동작하는 상태 유지)
  │
  └── develop ─── 통합 브랜치
        │
        ├── feature/cv-pipeline         (김현섭)
        ├── feature/rule-engine         (윤수민)
        ├── feature/genai-integration   (김현섭)
        ├── feature/frontend-ui         (팀 협의)
        └── feature/mlops-infra         (이윤호, 서지은)
```

**PR 규칙:**
- PR은 반드시 1명 이상 리뷰 후 머지
- main 직접 push 금지
- 커밋 메시지 형식: `[feat/fix/docs/refactor] 작업 내용`

---

## 5. 스토리지 설계

### 5-1. 이미지 저장 정책

```
생성된 캐릭터 이미지
    │
    ▼
S3 / Cloudflare R2 업로드
    │
    ├─ 경로: /results/{uuid}/{timestamp}_character.png
    ├─ 접근: Public Read (결과 공유용)
    └─ 보존 기간: 24시간 후 자동 삭제 (TTL 정책)

원본 업로드 이미지
    ├─ 서버 메모리에서만 처리 (디스크 저장 안 함)
    └─ 처리 완료 즉시 메모리에서 제거
```

### 5-2. API 명세 (핵심 엔드포인트)

```
POST /api/v1/analyze
  - Content-Type: multipart/form-data
  - Body: { image: File }
  - Response:
    {
      "status": "success",
      "character": {
        "type": "수생형",
        "element": "물 속성",
        "mood": "온화한",
        "face_base": "둥근 얼굴형 크리처",
        "name": "아쿠아렌"
      },
      "image_url": "https://cdn.../results/uuid/character.png",
      "story": "잔잔한 호수의 수호자...",
      "features_used": ["눈 간격 넓음", "안경 착용", "둥근 얼굴형"],
      "processing_time_ms": 14320
    }

GET /api/v1/health
  - Response: { "status": "ok", "version": "1.0.0" }
```

---

## 6. 모니터링 및 관측성

### 6-1. 로깅 구조

```python
# 각 파이프라인 단계별 로그 형식
{
    "request_id": "uuid-v4",
    "timestamp": "ISO8601",
    "stage": "feature_extraction",        # 단계명
    "duration_ms": 320,                   # 소요 시간
    "success": true,
    "error_code": null,                   # 실패 시 에러 코드
    "metadata": { ... }                   # 단계별 추가 정보
}
```

### 6-2. 핵심 모니터링 지표 (KPI 연동)

| 지표 | 측정 방법 | 목표값 |
|------|----------|--------|
| 얼굴 검출 성공률 | 요청 대비 성공 건수 | > 80% |
| 평균 응답 시간 | 전체 파이프라인 end-to-end | < 20초 |
| API 에러율 | 5xx 응답 비율 | < 5% |
| GenAI API 비용 | 일별 API 호출 비용 추적 | 예산 내 |

### 6-3. 에러 추적

- **Sentry** 무료 플랜으로 예외 캡처
- 에러 발생 시 Discord 채널 Webhook 알림 연동

```python
# Sentry 설정 (main.py)
import sentry_sdk
sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
```

---

## 7. 보안 설계

| 항목 | 처리 방법 |
|------|----------|
| API Key 관리 | 환경변수만 사용, 코드에 하드코딩 절대 금지 |
| 이미지 업로드 | 파일 타입 + 크기 서버 측 검증 |
| 원본 이미지 | 메모리 처리 후 즉시 폐기, 디스크 저장 안 함 |
| CORS | 프론트 도메인만 허용 |
| Rate Limiting | 동일 IP 분당 10회 제한 (FastAPI middleware) |

---

## 8. 3주 MLOps 실행 계획

### 1주차 — 기반 구축

| 일자 | 담당 | 작업 |
|------|------|------|
| Day 1 | 전체 | **속성 매핑 테이블 확정 (최우선)** |
| Day 1 | 전체 | **API 명세 확정** |
| Day 1~2 | 이윤호 | Docker Compose 로컬 환경 세팅 |
| Day 1~2 | 이윤호 | GitHub Actions CI 기본 구성 |
| Day 2~3 | 서지은 | 이미지 전처리 파이프라인 구현 |
| Day 3~5 | 서지은 | MediaPipe 특징 추출 모듈 구현 |
| Day 3~5 | 김현섭 | FastAPI 기본 구조 + Mock 엔드포인트 |
| Day 3~5 | 윤수민 | Rule Engine 구현 + 프론트 Mock UI |

### 2주차 — 핵심 기능 연결

| 일자 | 담당 | 작업 |
|------|------|------|
| Day 6~7 | 김현섭 | GenAI 이미지 생성 연동 |
| Day 6~7 | 김현섭 | LLM 스토리 생성 연동 |
| Day 7~8 | 서지은 | 병렬 처리 (asyncio.gather) 적용 |
| Day 8~9 | 이윤호 | S3 스토리지 연동 + 이미지 TTL |
| Day 8~10 | 이윤호 | Railway/EC2 배포 환경 구성 |
| Day 9~10 | 전체 | 내부 테스트 + 에러 케이스 처리 |

### 3주차 — 안정화 및 발표 준비

| 일자 | 담당 | 작업 |
|------|------|------|
| Day 11~12 | 전체 | 실사용자 테스트 (팀원 사진 20장 이상) |
| Day 12~13 | 서지은 | 실패 케이스 개선 + 재시도 로직 |
| Day 13~14 | 이윤호 | Sentry 모니터링 + Discord 알림 연동 |
| Day 14~15 | 이윤호 | 최종 배포 안정화 |
| Day 14~15 | 윤수민 | 발표 자료 + 데모 시나리오 |

---

## 9. 위험 대응 플랜 (Contingency)

| 상황 | 1차 대응 | 2차 대응 |
|------|----------|----------|
| GenAI API 속도 초과/비용 | 생성 결과 캐싱 (동일 속성 재사용) | 사전 생성된 에셋 풀로 대체 |
| MediaPipe 정확도 낮음 | 임계값 조정 + 예외처리 강화 | 단순 얼굴 비율만 사용하는 fallback |
| 배포 환경 문제 | 로컬 ngrok 터널로 데모 | Colab + ngrok 임시 대체 |
| 응답 시간 20초 초과 | 로딩 UX 강화로 체감 개선 | 이미지 생성 품질 낮춰 속도 우선 |

---

## 10. requirements.txt (Backend)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
opencv-python-headless==4.9.0.80
mediapipe==0.10.14
numpy==1.26.4
Pillow==10.3.0
boto3==1.34.0          # S3 연동
openai==1.30.0         # GPT-4o / DALL-E 3
anthropic==0.25.0      # Claude API (선택)
sentry-sdk[fastapi]==2.5.0
httpx==0.27.0          # 비동기 HTTP 클라이언트
python-dotenv==1.0.1
pydantic-settings==2.2.1
```

---

*본 설계서는 MVP 3주 기준으로 작성되었으며, 서비스 확장 시 Redis 큐, 비동기 워커(Celery), 전용 GPU 서버 도입을 검토한다.*
