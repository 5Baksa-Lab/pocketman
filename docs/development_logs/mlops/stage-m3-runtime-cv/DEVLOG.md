# Stage 개발일지

## 0) 기본 정보
- 파트: `mlops`
- Stage: `m3-runtime-cv`
- 작성자: `김현섭 (사후 분석 작성)`
- 작성일: `2026-03-09`
- 관련 이슈/PR: `N/A — 코드베이스 역분석 기반 작성`

## 1) Stage 목표/범위
- 목표:
  - 사용자 얼굴 이미지에서 28차원 벡터를 실시간으로 생성하는 CV 모듈 구현
  - Backend `cv_adapter.py`와 연동하여 `/api/v1/match`에서 활용 가능한 상태 달성
- 이번 Stage에서 포함한 범위:
  - `scripts/user_poc/` 패키지 (extractor.py, config.py, schema.py)
  - `scripts/07_extract_user_features_poc.py`, `08_validate_user_extraction_poc.py`
  - `backend/app/adapter/cv_adapter.py`

## 2) 구현 상세
### 2.1 핵심 설계/의사결정
- 결정 1: **MediaPipe Face Mesh(Primary) + Haar Cascade(Fallback) 이중 구조**
- 결정 2: **`user_poc` 패키지를 `scripts/` 하위에 배치, Backend가 import**
  - `cv_adapter.py`의 `_SCRIPT_CANDIDATES` 경로 탐색:
    1. `<repo_root>/scripts` (로컬)
    2. `<app_root>/scripts` (컨테이너)
    3. `/app/scripts` (Docker 절대)
- 결정 3: **품질 점수 < 0.15 시 LOW_QUALITY 에러**
  - `quality = face_area_ratio×1.6 + sharpness_norm×0.4`

### 2.2 핵심 로직 설명
- `UserFaceFeatureExtractor.extract(image_path)`:
  - MediaPipe 468 랜드마크 → 기하학적 계산 (eye_size, eye_distance, eye_slant, face_aspect, jawline, smile_score 등)
  - Boolean: has_glasses (Canny edge density), has_facial_hair (HSV), has_bangs (HSV)
  - 감정 7분류: smile_score + eye_tail 기반 규칙
  - dominant_color: K-means(k=3)
- `build_user_vector(image_bytes)` in `cv_adapter.py`:
  - bytes → 임시 파일 → extract() → impression 계산 → affinity 계산 → 28D 조립 → L2 정규화

### 2.3 변경 파일 목록
- `scripts/user_poc/__init__.py`, `config.py`, `schema.py`, `extractor.py` (455줄)
- `scripts/07_extract_user_features_poc.py`: PoC 배치 추출
- `scripts/08_validate_user_extraction_poc.py`: PoC 결과 검증
- `backend/app/adapter/cv_adapter.py`: Backend 연동 어댑터 (146줄)
- `backend/Dockerfile`: `scripts/user_poc/`, `scripts/shared/` COPY 추가

## 3) 테스트/검증
### 3.1 실행한 테스트
- `python3 scripts/07_extract_user_features_poc.py --limit 20`
- `python3 scripts/08_validate_user_extraction_poc.py --csv outputs/...`
- ※ 실제 결과 수치 없음 (사후 작성)

### 3.2 수동 검증
- 정면 사진 → 20컬럼 유효값 생성 확인
- 얼굴 없는 이미지 → `FACE_NOT_DETECTED` 반환 확인
- 두 명 이상 → `MULTIPLE_FACES` 반환 확인

## 4) 이슈/리스크
- **버그: `cv_adapter.py` 임시 파일 누수**
  - `extractor.extract()` 예외 시 `os.unlink` 미실행
  - 수정 필요:
    ```python
    try:
        result, _ = extractor.extract(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    ```
- MediaPipe 버전 업데이트 시 랜드마크 인덱스 변경 가능성
- 안경 감지: Canny edge 기반 → 조명 민감, 오탐 가능

## 5) 다음 Stage 인수인계 (B2)
- `cv_adapter.py` try/finally 즉시 수정 필요
- Docker 컨테이너 내부 import 성공 확인 필수
- `scripts/user_poc/config.py` RANGE 값 변경 시 포켓몬 벡터와 분포 불일치 발생

## 6) AI 활용 기록
- 사용한 AI: Claude Sonnet 4.6
- 수동 수정: 임시 파일 누수 이슈 직접 명시 + 수정 코드 제시

## 7) 완료 체크
- [x] MediaPipe 기반 특징 추출기 구현 완료
- [x] Haar Cascade fallback 구현 완료
- [x] Backend `cv_adapter.py` 연동 구현 완료
- [ ] **임시 파일 try/finally 수정 (미완 — 버그)**
- [ ] 실 20장 PoC 테스트 결과 증빙 (사후 작성으로 누락)
- [x] 개발일지 파일 생성: `docs/development_logs/mlops/stage-m3-runtime-cv/DEVLOG.md`
- [ ] PM/리드 리뷰 완료
