# Stage 개발일지

## 0) 기본 정보
- 파트: `pm-devops`
- Stage: `p3-release-demo`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 사후 작성 / 미완료 Stage`

## 1) Stage 목표/범위
- 목표:
  - E2E 시나리오 3회 연속 성공으로 데모 준비 완료
  - 고심각도 리스크 처리 (CORS, 임시 파일 누수)
  - Plan A/B 전환 기준 점검
- ⚠️ **이 Stage는 아직 완료되지 않았습니다.**

## 2) 미완료 항목 현황

| 항목 | 우선순위 | 상태 |
|---|---|---|
| `cv_adapter.py` try/finally 수정 | 높음 | ❌ 미완 |
| CORS `allow_origins` 제한 | 높음 | ❌ 미완 |
| DB 커넥션 풀 구현 | 중간 | ❌ 미완 |
| 카카오톡 공유 결정 | 중간 | ❌ 미결정 |
| E2E 시나리오 3회 연속 성공 | 높음 | ❌ 미수행 |
| 이름 편집 서버 반영 | 낮음 | ❌ 미완 |

## 3) 즉시 처리 필요 수정 코드

### cv_adapter.py 수정 (`backend/app/adapter/cv_adapter.py`)
```python
# 현재 (버그)
extractor = UserFaceFeatureExtractor()
result, _ = extractor.extract(tmp_path)
os.unlink(tmp_path)

# 수정 후
try:
    extractor = UserFaceFeatureExtractor()
    result, _ = extractor.extract(tmp_path)
finally:
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
```

### CORS 제한 (`backend/app/main.py`)
```python
# 현재
allow_origins=["*"]

# 수정 후
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allow_origins=[FRONTEND_URL]
```

### DB 커넥션 풀 (`backend/app/core/db.py`)
```python
from psycopg2 import pool as pgpool
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pgpool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)
    return _pool

def get_connection():
    return get_pool().getconn()
```

## 4) E2E 데모 시나리오 (Plan A)
1. `http://localhost:3000` 접속
2. 정면 얼굴 사진 업로드
3. "매칭 시작" → 약 2초 후 Top-3 포켓몬 표시
4. 포켓몬 선택 → "내 크리처 만들기"
5. 이름/스토리/이미지 생성 (~10-15초) + Veo 폴링 (~1-3분)
6. 결과 화면 → URL 복사 또는 Twitter 공유
7. "광장에 등록" → `/plaza` 이동 → 이모지 리액션

## 5) Plan B 전환 기준

| 조건 | Plan B |
|---|---|
| Veo 완료율 70% 미만 | CSS 애니메이션 fallback 기본 모드 |
| Gemini/Imagen 쿼터 초과 | USE_MOCK_AI=true 전환 |
| DB 연결 불가 | Docker DB 재기동 + 스키마 재적용 |

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 미완료 현황 표, 수정 코드 스니펫 직접 작성

## 7) 완료 체크 (현재 미완)
- [ ] cv_adapter.py try/finally 수정
- [ ] CORS 제한
- [ ] DB 커넥션 풀
- [ ] E2E 시나리오 3회 연속 성공
- [ ] 카카오톡 공유 결정
- [x] 미완료 항목 + 수정 코드 문서화 완료
- [x] 개발일지 파일 생성: `docs/development_logs/pm-devops/stage-p3-release-demo/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
