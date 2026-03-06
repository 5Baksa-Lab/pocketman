# 포켓몬 DB 구축 스크립트

## 실행 전 준비

### 1. 의존성 설치
```bash
pip install -r scripts/requirements.txt
```

### 2. 환경변수 설정 (.env 파일)
```
DATABASE_URL=postgresql://pokeman_user:password@localhost:5432/pokeman_db
GEMINI_API_KEY=your_api_key_here
USE_MOCK_AI=true   # 개발 중에는 true, 실제 배포 전 false로 전환
```

### 3. DB 컨테이너 실행 및 DDL 적용
```bash
docker compose up -d db
psql $DATABASE_URL -f database/포켓몬_DDL_gen1_v1.sql
```

---

## 실행 순서

```bash
# Step 1. PokeAPI 배치 수집 (약 30분)
python scripts/01_fetch_pokeapi.py

# Step 2. Gemini Vision 시각 특징 주석 (약 2시간, Mock 시 5분)
USE_MOCK_AI=true python scripts/02_annotate_gemini_vision.py

# Step 3. 인상 점수 자동 계산 (약 10분)
python scripts/03_calc_impression.py

# Step 4. 타입 친화도 자동 계산 (약 5분)
python scripts/04_calc_type_affinity.py

# Step 5. 28차원 벡터 생성 (약 5분)
python scripts/05_build_vectors.py

# Step 6. 전체 검증
python scripts/06_validate.py --sample-match

# Step 7. 사용자 이미지 특징 추출 PoC
python scripts/07_extract_user_features_poc.py --input-dir scripts/poc_images

# Step 8. 사용자 추출 결과 검증
python scripts/08_validate_user_extraction_poc.py \
  --csv outputs/user_poc/user_face_features_poc.csv \
  --debug-csv outputs/user_poc/user_face_features_poc_debug.csv
```

---

## 유용한 옵션

| 스크립트 | 옵션 | 설명 |
|---------|------|------|
| 01 | `--dry-run` | DB 저장 없이 수집 결과 출력 |
| 01, 02~05 | `--start 1 --end 30` | 범위 지정 실행 |
| 02 | `--retry-failed` | 실패 항목만 재실행 |
| 06 | `--sample-match` | 피카츄 기준 유사도 검색 테스트 |

---

## 스크립트별 역할

| 파일 | 역할 | 저장 테이블 |
|------|------|-----------|
| `01_fetch_pokeapi.py` | PokeAPI 배치 수집 | pokemon_master, pokemon_stats |
| `02_annotate_gemini_vision.py` | Gemini Vision 시각 주석 | face_shape, eye, nose_mouth, style, emotion |
| `03_calc_impression.py` | 인상 점수 계산 | pokemon_impression_scores |
| `04_calc_type_affinity.py` | 타입 친화도 계산 | pokemon_type_affinity |
| `05_build_vectors.py` | 28차원 벡터 생성 | pokemon_feature_vectors |
| `06_validate.py` | 전체 검증 | (읽기 전용) |
| `07_extract_user_features_poc.py` | 사용자 이미지 특징 추출 PoC | user_face_features (선택) |
| `08_validate_user_extraction_poc.py` | 사용자 추출 결과 검증 | (읽기 전용) |

---

## 사용자 이미지 추출 PoC 추가 설정

### 1) 입력 이미지 폴더

`scripts/poc_images` 디렉토리에 테스트 이미지를 넣습니다.

### 2) PoC 테이블 생성 (선택)

```bash
psql $DATABASE_URL -f database/사용자_얼굴특징_PoC_DDL_v1.sql
```

### 3) DB 저장 포함 실행 예시

```bash
python scripts/07_extract_user_features_poc.py \
  --input-dir scripts/poc_images \
  --write-db \
  --table-name user_face_features
```

### 4) 결과 파일

- `outputs/user_poc/user_face_features_poc.csv`
  - `User_Face_Features` 실스키마 20컬럼 1:1
- `outputs/user_poc/user_face_features_poc_debug.csv`
  - PoC 디버그 메타 컬럼(`poc_status`, `poc_error_code`, `poc_quality_score`)
