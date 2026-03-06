# User Feature Extraction PoC

이 모듈은 `User_Face_Features` 실스키마(20개 컬럼) 1:1 기준으로 사용자 이미지를 추출/검증하기 위한 PoC 구현입니다.

## 구성

- `config.py`: 랜드마크 인덱스, 정규화 범위, 임계값
- `schema.py`: 실스키마 컬럼(20개), row sanitize, 실패 row 기본값
- `extractor.py`: 실제 추출 로직(MediaPipe + OpenCV)

## 상위 실행 스크립트

- `scripts/07_extract_user_features_poc.py`
- `scripts/08_validate_user_extraction_poc.py`

## 출력 파일

- `outputs/user_poc/user_face_features_poc.csv`: 실스키마 20컬럼 CSV
- `outputs/user_poc/user_face_features_poc_debug.csv`: PoC 메타(`poc_status`, `poc_error_code`, `poc_quality_score`)
- `outputs/user_poc/json/*.json`: 이미지별 상세 결과(JSON)
- `outputs/user_poc/overlays/*_overlay.jpg`: 디버그 오버레이 이미지

## 주의

- `has_glasses`, `has_facial_hair`, `has_bangs`, `emotion_class`는 PoC 단계의 휴리스틱입니다.
- 정밀도 평가는 샘플 라벨셋 기반으로 별도 보정이 필요합니다.
