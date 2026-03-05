# Pokéman MLOps 파이프라인 설계서 (Ollama 홈 서버 버전)

**작성일:** 2026년 3월 5일
**작성자:** 시니어 MLOps 엔지니어
**버전:** v2.0 (Ollama 홈 GPU 서버 + Veo API 반영)
**전제 조건:** 팀 선택 A-3 (Ollama 홈 서버 + 외부 LLM 혼합) 기준

---

## 0. 설계 전제

| 항목 | 내용 |
|------|------|
| LLM 서버 | 홈 GPU 데스크톱 + Ollama (Cloudflare Tunnel로 외부 노출) |
| 멀티모달 분석 | llama3.2-vision (Ollama) |
| 스토리/이름 생성 | 외부 LLM API (Gemini Flash 또는 GPT-4o-mini) |
| 이미지 생성 | Imagen 3 (Google Gemini API) |
| 영상 생성 | Veo API (비동기 처리) |
| 배포 | Frontend → Vercel / Backend → Railway / Ollama → 홈 서버 |

---

## 1. 전체 인프라 구성도

```
┌─────────────────────────────────────────────────────────────────────┐
│                         사용자 (브라우저)                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Vercel (Frontend - Next.js)                       │
│  - 사진 업로드 UI                                                   │
│  - 영상 생성 중 Polling UI                                          │
│  - 스토리북 영상 플레이어                                           │
│  - 포켓 도감 광장 피드                                              │
│  - 외부 공유 버튼 (카카오 / 트위터 / URL)                           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Railway (Backend - FastAPI + Docker)                │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ 1.전처리    │→ │ 2.CV 추출    │→ │ 3.멀티모달 분석          │   │
│  │ OpenCV      │  │ MediaPipe    │  │ → Ollama API 호출         │   │
│  └─────────────┘  └──────────────┘  └──────────────────────────┘   │
│                                               │                      │
│                              ┌────────────────┘                     │
│                              │ 속성값 확정                           │
│                              ▼                                       │
│         ┌────────────────────┬─────────────────────┐               │
│         │ (병렬 처리)         │                     │               │
│         ▼                    ▼                     ▼               │
│  ┌─────────────┐   ┌──────────────┐    ┌──────────────────────┐   │
│  │ 4.이미지생성 │   │ 5.스토리생성 │    │ 6.Veo 영상 생성 시작 │   │
│  │ Imagen 3    │   │ 외부 LLM API │    │ (비동기 Job 등록)    │   │
│  └─────────────┘   └──────────────┘    └──────────────────────┘   │
│         │                    │                     │               │
│         └────────────────────┘                     │               │
│                    │ 즉시 반환                       │ Job ID 반환  │
│                    ▼                               ▼               │
│             S3 저장 + DB 기록              Veo 완료 Polling         │
└─────────────────────────────────────────────────────────────────────┘
          │                                          │
          ▼                                          ▼
┌──────────────────┐                    ┌────────────────────────┐
│  홈 GPU 서버     │                    │     외부 API 서버       │
│  (Ollama)        │                    │  - Imagen 3 (Google)   │
│  - llama3.2-     │                    │  - Veo (Google)        │
│    vision:11b    │                    │  - Gemini Flash (LLM)  │
│  Cloudflare      │                    └────────────────────────┘
│  Tunnel 경유     │
└──────────────────┘
          │
┌──────────────────┐    ┌──────────────┐    ┌──────────────────┐
│ S3 / R2 Storage  │    │  PostgreSQL  │    │  Sentry + Discord │
│ 이미지 + 영상    │    │  크리처 DB   │    │  에러 모니터링    │
└──────────────────┘    └──────────────┘    └──────────────────┘
```

---

## 2. Ollama 홈 서버 구성 상세

### 2-1. 설치 및 모델 준비

```bash
# 1. Ollama 설치 (데스크톱)
curl -fsSL https://ollama.com/install.sh | sh

# 2. 멀티모달 모델 다운로드
ollama pull llama3.2-vision      # 얼굴 분석용 (약 7GB)

# 3. 텍스트 전용 모델 (스토리 생성 Fallback용 - 선택)
ollama pull gemma3:12b            # 스토리 생성 Fallback

# 4. 서버 실행 확인
ollama serve
# → http://localhost:11434 에서 실행
```

### 2-2. Cloudflare Tunnel 구성

```bash
# 1. cloudflared 설치
# Windows: https://github.com/cloudflare/cloudflared/releases 에서 다운로드
# Mac: brew install cloudflared

# 2. Cloudflare 계정 인증
cloudflared tunnel login

# 3. 터널 생성
cloudflared tunnel create pokeman-ollama

# 4. 설정 파일 작성
# ~/.cloudflared/config.yml
tunnel: pokeman-ollama
credentials-file: /Users/{username}/.cloudflared/{tunnel-id}.json

ingress:
  - hostname: ollama.pokeman.app    # 팀 도메인 설정
    service: http://localhost:11434
  - service: http_status:404

# 5. 터널 실행
cloudflared tunnel run pokeman-ollama

# 6. 시스템 시작 시 자동 실행 등록 (중요!)
# Windows: 서비스 등록
# Mac: launchctl 등록
```

```
결과:
https://ollama.pokeman.app → 집 데스크톱 Ollama API
외부에서 접근 가능, HTTPS 자동, 포트포워딩 불필요
```

### 2-3. GPU 스펙별 권장 설정

```
NVIDIA RTX 3060 (12GB VRAM):
  모델: llama3.2-vision:11b
  예상 응답 시간: 3~5초
  동시 처리: 1~2 요청

NVIDIA RTX 3080/3090 (10~24GB VRAM):
  모델: llama3.2-vision:11b + gemma3:12b 동시 운용
  예상 응답 시간: 1~3초
  동시 처리: 2~3 요청

NVIDIA RTX 4070/4080/4090:
  모델: llama3.2-vision:11b (권장)
  예상 응답 시간: 1~2초
  동시 처리: 3+ 요청
```

---

## 3. CV + 멀티모달 파이프라인 상세

### 3-1. 전처리 → MediaPipe → Ollama 흐름

```python
# pipeline/cv_pipeline.py

import cv2
import mediapipe as mp
import httpx
import base64
from typing import dict

async def run_cv_pipeline(image_bytes: bytes) -> dict:

    # Step 1: OpenCV 전처리
    img = preprocess_image(image_bytes)
    # - 리사이즈 (최대 1280px)
    # - BGR → RGB 변환
    # - 블러 감지 (Laplacian variance < 50 → 경고)

    # Step 2: MediaPipe 얼굴 검출
    face_result = detect_face(img)
    if not face_result.success:
        raise FaceNotDetectedException(face_result.error_code)

    # Step 3: 수치 특징 추출 (Rule-based 백업용)
    numeric_features = extract_numeric_features(face_result.landmarks)
    # {
    #   "eye_distance_ratio": 0.42,
    #   "face_shape_ratio": 1.3,
    #   "has_glasses": True,
    #   "eyebrow_angle": 12.5,
    # }

    # Step 4: Ollama 멀티모달 분석 (메인)
    image_b64 = base64.b64encode(image_bytes).decode()
    ollama_result = await analyze_with_ollama(image_b64, numeric_features)

    return ollama_result


async def analyze_with_ollama(image_b64: str, numeric_hints: dict) -> dict:

    # Few-shot 프롬프트 구성
    prompt = f"""
당신은 얼굴 이미지를 분석하여 크리처 캐릭터 속성을 결정하는 전문가입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

[참고 수치 데이터]
- 눈 간격 비율: {numeric_hints['eye_distance_ratio']:.2f} (0.45 이상이면 넓음)
- 얼굴 장단비: {numeric_hints['face_shape_ratio']:.2f} (1.4 이상이면 갸름)
- 안경 착용: {numeric_hints['has_glasses']}
- 눈썹 각도: {numeric_hints['eyebrow_angle']:.1f}도

[Few-shot 예시]
예시 1 - 눈이 크고 둥근 얼굴, 부드러운 인상:
{{"type": "수생형", "mood": "온화한", "element": "물", "face": "둥근형", "key_feature": "큰 눈", "pokemon_match": "라프라스"}}

예시 2 - 갸름한 얼굴, 안경 착용, 날카로운 눈썹:
{{"type": "지능형", "mood": "날카로운", "element": "번개", "face": "갸름형", "key_feature": "안경", "pokemon_match": "마자용"}}

예시 3 - 각진 턱, 강한 인상, 두꺼운 눈썹:
{{"type": "전사형", "mood": "강렬한", "element": "불", "face": "각진형", "key_feature": "강한 눈썹", "pokemon_match": "갸라도스"}}

예시 4 - 작고 귀여운 이목구비, 밝은 인상:
{{"type": "요정형", "mood": "발랄한", "element": "빛", "face": "둥근형", "key_feature": "작은 이목구비", "pokemon_match": "이브이"}}

이제 제공된 이미지와 수치 데이터를 바탕으로 분석하세요:
"""

    response = await httpx.AsyncClient(timeout=30.0).post(
        f"{settings.OLLAMA_HOST}/api/generate",
        json={
            "model": "llama3.2-vision",
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "format": "json",         # JSON 형식 강제
            "options": {
                "temperature": 0.3,   # 낮은 temperature로 일관성 확보
                "top_p": 0.9,
            }
        }
    )

    return parse_ollama_response(response.json())
```

### 3-2. Ollama 장애 시 Fallback

```python
async def analyze_with_fallback(image_b64: str, numeric_hints: dict) -> dict:
    try:
        # 1차: Ollama 홈 서버 시도
        return await analyze_with_ollama(image_b64, numeric_hints)

    except (httpx.ConnectError, httpx.TimeoutException):
        # Ollama 서버 다운 → Rule-based 자동 전환
        logger.warning("Ollama 서버 연결 실패 → Rule-based Fallback 실행")
        return rule_based_mapping(numeric_hints)

    except Exception as e:
        # 예상치 못한 에러 → Rule-based 자동 전환
        logger.error(f"Ollama 분석 실패: {e} → Rule-based Fallback 실행")
        return rule_based_mapping(numeric_hints)


def rule_based_mapping(features: dict) -> dict:
    """Ollama 없이 수치만으로 속성 결정 (Fallback)"""
    type_ = "수생형" if features["eye_distance_ratio"] > 0.45 else \
            "조류형" if features["eye_distance_ratio"] < 0.35 else "포유형"

    element = "지능/물" if features["has_glasses"] else "자연/불"

    mood = "날카로운" if features["eyebrow_angle"] > 15 else \
           "온화한" if features["eyebrow_angle"] < -5 else "중립적"

    return {
        "type": type_,
        "mood": mood,
        "element": element,
        "face": "갸름형" if features["face_shape_ratio"] > 1.4 else "둥근형",
        "key_feature": "안경" if features["has_glasses"] else "눈 비율",
        "source": "rule_based"  # Fallback 여부 표시
    }
```

---

## 4. AI 생성 파이프라인 상세

### 4-1. 병렬 처리 구조

```python
# pipeline/generation_pipeline.py

async def generate_all(character_attrs: dict, image_b64: str) -> dict:
    """
    이미지 생성 + 스토리 생성을 병렬로 실행
    Veo 영상은 별도 비동기 Job으로 등록
    """

    # 이미지 + 스토리 병렬 생성
    image_task = asyncio.create_task(
        generate_creature_image(character_attrs)
    )
    story_task = asyncio.create_task(
        generate_story_and_name(character_attrs)
    )

    image_url, story_result = await asyncio.gather(image_task, story_task)

    # Veo 영상 생성은 비동기 Job으로 등록 후 즉시 반환
    veo_job_id = await register_veo_job(image_url, character_attrs, story_result)

    return {
        "image_url": image_url,
        "name_suggestion": story_result["name"],
        "story": story_result["story"],
        "character": character_attrs,
        "veo_job_id": veo_job_id,   # 프론트가 Polling에 사용
    }


async def generate_creature_image(attrs: dict) -> str:
    """Imagen 3로 크리처 이미지 생성"""

    prompt = f"""
original creature character design, {attrs['type']},
{attrs['element']} element, {attrs['mood']} expression,
{attrs['face']} face shape, key feature: {attrs['key_feature']},
game illustration style, full body, clean white background,
high quality, fantasy monster, NOT existing IP character
""".strip()

    negative_prompt = """
realistic photo, human face, anime style, chibi,
pikachu, pokemon, existing game character, watermark,
low quality, blurry, text overlay
"""

    # Imagen 3 API 호출
    response = await call_imagen3(prompt, negative_prompt)
    image_url = await upload_to_s3(response.image_bytes)
    return image_url


async def generate_story_and_name(attrs: dict) -> dict:
    """외부 LLM API로 스토리 + 이름 생성"""

    prompt = f"""
다음 크리처 속성을 바탕으로 아래 두 가지를 생성하세요.

속성:
- 타입: {attrs['type']}
- 속성: {attrs['element']}
- 분위기: {attrs['mood']}
- 특징: {attrs['key_feature']}

1. 이름: 해당 크리처에 어울리는 이름 1개 (6자 이내, 신비롭고 기억에 남는)
2. 스토리: 50자 이내의 도감 소개 문구 (1~2문장, 감성적으로)

반드시 JSON으로 응답: {{"name": "...", "story": "..."}}
"""

    # 외부 LLM API 호출 (Gemini Flash 또는 GPT-4o-mini)
    result = await call_external_llm(prompt)
    return result
```

### 4-2. Veo 비동기 파이프라인

Veo 영상 생성은 1~3분이 소요되므로 반드시 비동기 구조가 필요합니다.

```
[요청 흐름]

사용자 요청
    │
    ▼
FastAPI: Veo Job 등록
    │ veo_job_id 즉시 반환
    ▼
프론트: "영상 생성 중..." 화면 표시
    │
    │ 3초마다 GET /api/v1/veo/status/{veo_job_id} Polling
    │
    ├─ status: "processing" → 계속 대기
    └─ status: "completed"  → video_url 수신 → 영상 재생
```

```python
# api/veo_router.py

@router.post("/api/v1/veo/generate")
async def start_veo_generation(request: VeoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    # DB에 Job 등록 (pending 상태)
    await db.create_veo_job(job_id, status="pending")

    # 백그라운드에서 Veo API 호출
    background_tasks.add_task(run_veo_job, job_id, request)

    return {"veo_job_id": job_id, "status": "pending"}


@router.get("/api/v1/veo/status/{job_id}")
async def get_veo_status(job_id: str):
    job = await db.get_veo_job(job_id)

    if job.status == "completed":
        return {
            "status": "completed",
            "video_url": job.video_url,
        }
    elif job.status == "failed":
        return {
            "status": "failed",
            "fallback": "css_animation",  # 프론트에 CSS Fallback 신호
        }
    else:
        return {"status": "processing"}


async def run_veo_job(job_id: str, request: VeoRequest):
    try:
        await db.update_veo_job(job_id, status="processing")

        # Veo API 호출
        video_bytes = await call_veo_api(
            image_url=request.image_url,
            prompt=f"{request.character_type} creature, {request.mood} movement, "
                   f"magical aura, fantasy style, 15 seconds"
        )

        # S3 업로드
        video_url = await upload_video_to_s3(video_bytes, job_id)

        await db.update_veo_job(job_id, status="completed", video_url=video_url)

    except Exception as e:
        logger.error(f"Veo 생성 실패 job_id={job_id}: {e}")
        await db.update_veo_job(job_id, status="failed")
        # 프론트는 failed 수신 시 CSS Fallback으로 자동 전환
```

---

## 5. 인프라 구성 상세

### 5-1. 환경별 구성

```
┌─────────────────────────────────────────────────────────┐
│  로컬 개발 환경                                          │
│  docker-compose up                                      │
│    - FastAPI (localhost:8000)                           │
│    - PostgreSQL (localhost:5432)                        │
│    - Ollama는 직접 로컬 실행 (localhost:11434)           │
│    - 외부 API는 실제 호출 또는 Mock 전환                 │
└─────────────────────────────────────────────────────────┘
                    │ git push main
                    ▼
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (CI)                                    │
│    - pytest 자동 실행                                   │
│    - Docker 이미지 빌드 테스트                          │
│    - 통과 시 Railway 자동 배포                          │
└─────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼──────────────┐
        ▼           ▼              ▼
   [Vercel]    [Railway]      [홈 데스크톱]
   Frontend    Backend        Ollama 서버
   Next.js     FastAPI        llama3.2-vision
               PostgreSQL     Cloudflare Tunnel
               S3 연동
```

### 5-2. Docker Compose (로컬 개발용)

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env.local
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434  # 로컬 Ollama 접근
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: pokeman
      POSTGRES_USER: pokeman
      POSTGRES_PASSWORD: localpassword
    volumes:
      - postgres_data:/var/lib/postgresql/data

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    env_file: .env.local
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 5-3. 환경변수 구성

```bash
# .env.local (절대 Git에 커밋 금지)

# Ollama 서버
OLLAMA_HOST=https://ollama.pokeman.app    # Cloudflare Tunnel URL
OLLAMA_MODEL=llama3.2-vision
OLLAMA_TIMEOUT=30

# 외부 AI API
GOOGLE_API_KEY=your_google_api_key        # Imagen 3 + Veo + Gemini Flash
OPENAI_API_KEY=your_openai_api_key        # GPT-4o-mini (선택)

# 스토리지
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=pokeman-assets
S3_REGION=ap-northeast-2

# DB
DATABASE_URL=postgresql://pokeman:password@localhost:5432/pokeman

# 모니터링
SENTRY_DSN=your_sentry_dsn

# 카카오 공유
KAKAO_JS_KEY=your_kakao_key
```

### 5-4. Dockerfile (Backend)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# OpenCV + MediaPipe 의존 라이브러리
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    libgl1-mesa-glx libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6. DB 스키마 (PostgreSQL)

```sql
-- 크리처 테이블
CREATE TABLE creatures (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(20) NOT NULL,
    type        VARCHAR(20) NOT NULL,
    element     VARCHAR(20) NOT NULL,
    mood        VARCHAR(20) NOT NULL,
    key_feature VARCHAR(50),
    story       TEXT NOT NULL,
    image_url   TEXT NOT NULL,
    video_url   TEXT,           -- Veo 영상 완료 후 업데이트
    is_public   BOOLEAN DEFAULT FALSE,  -- 광장 등록 여부 (Opt-in)
    created_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP          -- 24시간 후 삭제 (선택)
);

-- Veo Job 테이블
CREATE TABLE veo_jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id  UUID REFERENCES creatures(id),
    status       VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
    video_url    TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);

-- 이모지 리액션 테이블
CREATE TABLE reactions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id  UUID REFERENCES creatures(id),
    emoji_type   VARCHAR(20) NOT NULL,  -- 'warm' / 'mysterious' / 'natural'
    created_at   TIMESTAMP DEFAULT NOW()
);
```

---

## 7. API 명세

```
POST /api/v1/analyze
  요청: multipart/form-data { image: File }
  응답: {
    "creature_id": "uuid",
    "image_url": "https://s3.../creature.png",
    "name_suggestion": "아쿠아렌",
    "story": "잔잔한 호수의 수호자...",
    "character": { type, element, mood, face, key_feature },
    "veo_job_id": "uuid",
    "analysis_source": "ollama" or "rule_based"  // Fallback 여부
  }

GET /api/v1/veo/status/{job_id}
  응답: {
    "status": "pending" | "processing" | "completed" | "failed",
    "video_url": "https://s3.../video.mp4",  // completed 시
    "fallback": "css_animation"               // failed 시
  }

PATCH /api/v1/creature/{creature_id}/name
  요청: { "name": "사용자가 직접 입력한 이름" }
  응답: { "creature_id": "uuid", "name": "새 이름" }

POST /api/v1/creature/{creature_id}/publish
  요청: { "consent": true }
  응답: { "creature_id": "uuid", "is_public": true }

GET /api/v1/feed?page=1&limit=20
  응답: { "creatures": [...], "total": 120 }

POST /api/v1/reaction
  요청: { "creature_id": "uuid", "emoji_type": "warm" }
  응답: { "creature_id": "uuid", "warm": 5, "mysterious": 2, "natural": 1 }

GET /api/v1/health
  응답: {
    "status": "ok",
    "ollama": "connected" | "disconnected",  // 홈 서버 상태
    "version": "1.0.0"
  }
```

---

## 8. 모니터링 및 관측성

### 8-1. 단계별 성능 로깅

```python
# 각 단계 소요 시간 추적
{
    "request_id": "uuid",
    "stages": {
        "preprocessing":    120,   # ms
        "face_detection":   280,   # ms
        "ollama_analysis":  3420,  # ms  ← 홈 서버 응답 시간 추적
        "imagen3":          12300, # ms
        "llm_story":        2100,  # ms
        "veo_job_register": 450,   # ms
    },
    "total_to_first_response": 18670,  # ms (Veo 제외)
    "analysis_source": "ollama",       # or "rule_based" (Fallback 여부)
}
```

### 8-2. Ollama 서버 상태 모니터링

```python
# 30초마다 홈 서버 헬스체크
async def check_ollama_health():
    try:
        r = await httpx.AsyncClient(timeout=5.0).get(
            f"{settings.OLLAMA_HOST}/api/tags"
        )
        return r.status_code == 200
    except:
        # Discord Webhook으로 즉시 알림
        await send_discord_alert("🔴 Ollama 홈 서버 연결 끊김! Rule-based Fallback 자동 전환")
        return False
```

### 8-3. 핵심 KPI 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| 얼굴 검출 성공률 | > 80% | 요청 대비 성공 건수 |
| Ollama 응답 시간 | < 5초 | 단계별 로그 |
| 최초 응답 시간 (Veo 제외) | < 20초 | end-to-end 측정 |
| Veo 완료 시간 | < 3분 | Job 생성 ~ completed |
| Ollama Fallback 비율 | < 5% | rule_based 응답 비율 |
| API 에러율 | < 3% | 5xx 응답 비율 |

---

## 9. 발표 당일 체크리스트

```
D-1 (발표 전날):
  [ ] 홈 데스크톱 절전 모드 완전 해제
  [ ] Cloudflare Tunnel 실행 확인
  [ ] Ollama 모델 로드 상태 확인 (ollama list)
  [ ] /api/v1/health 엔드포인트로 전체 상태 확인
  [ ] 모바일 핫스팟 준비 (인터넷 백업)
  [ ] API 크레딧 잔액 확인 (Imagen 3, Veo)

D-day (발표 당일):
  [ ] 발표 시작 전 테스트 생성 1회 실행
  [ ] Discord 알림 채널 모니터링
  [ ] 팀원 1명이 서버 상태 전담 모니터링
  [ ] Fallback 시나리오 숙지 (Ollama 다운 → Rule-based 자동 전환)
```

---

## 10. requirements.txt (Backend)

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9

# CV
opencv-python-headless==4.9.0.80
mediapipe==0.10.14
numpy==1.26.4
Pillow==10.3.0

# AI API
google-generativeai==0.7.0    # Imagen 3 + Gemini Flash
openai==1.30.0                 # GPT-4o-mini (선택)
httpx==0.27.0                  # Ollama API 호출 (비동기)

# DB
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.30

# 스토리지
boto3==1.34.0

# 모니터링
sentry-sdk[fastapi]==2.5.0

# 설정
pydantic-settings==2.2.1
python-dotenv==1.0.1
```

---

## 11. 리스크 대응 플랜

| 상황 | 자동 대응 | 수동 대응 |
|------|----------|----------|
| Ollama 서버 다운 | Rule-based Fallback 자동 전환 | Discord 알림 → 팀원 서버 재시작 |
| Veo 생성 실패 | CSS Fallback 자동 전환 | 로그 확인 후 재시도 |
| Imagen 3 오류 | 재시도 1회 후 에러 반환 | API 크레딧 확인 |
| 발표 중 인터넷 단절 | — | 모바일 핫스팟으로 즉시 전환 |
| DB 연결 실패 | — | Railway 대시보드 재시작 |

---

*본 설계서는 Ollama 홈 서버 선택(A-2 또는 A-3) 시 적용되는 MLOps 파이프라인입니다.
팀 최종 결정에 따라 외부 API 전용 버전으로 전환 가능합니다.*
