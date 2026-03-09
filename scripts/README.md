# 포켓몬 DB 구축 스크립트

## 실행 전 준비

### 1. 의존성 설치

```bash
pip install -r scripts/requirements.txt
```

### 2. 환경변수 설정 (`.env`)

```dotenv
DATABASE_URL=postgresql://pocketman_user:pocketman_pass@localhost:5433/pocketman_db
GEMINI_API_KEY=your_api_key_here
USE_MOCK_AI=true
```

### 3. DB 컨테이너 실행 + 스키마 적용

```bash
docker compose up -d db
psql "$DATABASE_URL" -f database/01_schema.sql
```

## 실행 순서

```bash
# Step 1. PokeAPI 배치 수집 (ko 도감 + Fandom 보완)
python scripts/01_fetch_pokeapi.py

# Step 2. Gemini Vision 시각 특징 주석
USE_MOCK_AI=true python scripts/02_annotate_gemini_vision.py

# Step 3. 인상 점수 계산 (Gemini Flash + fallback)
python scripts/03_calc_impression.py

# Step 4. 타입 친화도 자동 계산
python scripts/04_calc_type_affinity.py

# Step 5. 28차원 벡터 생성
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

## 유용한 옵션

| 스크립트 | 옵션 | 설명 |
|---------|------|------|
| `01_fetch_pokeapi.py` | `--dry-run` | DB 저장 없이 수집 결과 출력 |
| `01_fetch_pokeapi.py` ~ `05_build_vectors.py` | `--start 1 --end 30` | 포켓몬 번호 범위 지정 |
| `02_annotate_gemini_vision.py` | `--retry-failed` | `pokemon_visual` 누락 항목만 재실행 |
| `06_validate.py` | `--sample-match` | 피카츄 기준 유사도 검색 테스트 포함 |

## 스크립트별 역할

| 파일 | 역할 | 저장 테이블 |
|------|------|-----------|
| `01_fetch_pokeapi.py` | PokeAPI 배치 수집 | `pokemon_master`, `pokemon_stats` |
| `02_annotate_gemini_vision.py` | Gemini Vision 시각 주석 | `pokemon_visual` |
| `03_calc_impression.py` | 인상 점수 계산 (Gemini Flash, 실패 시 규칙식 fallback) | `pokemon_impression` |
| `04_calc_type_affinity.py` | 타입 친화도 계산 | `pokemon_type_affinity` |
| `05_build_vectors.py` | 28차원 벡터 생성 | `pokemon_vectors` |
| `06_validate.py` | 전체 검증 | 읽기 전용 |
| `07_extract_user_features_poc.py` | 사용자 이미지 특징 추출 PoC | `user_face_features`(선택) |
| `08_validate_user_extraction_poc.py` | 사용자 추출 결과 검증 | 읽기 전용 |

## 사용자 이미지 추출 PoC

- 입력 이미지: `scripts/poc_images`
- 결과 CSV: `outputs/user_poc/user_face_features_poc.csv`
- 디버그 CSV: `outputs/user_poc/user_face_features_poc_debug.csv`

DB 저장까지 하려면:

```bash
python scripts/07_extract_user_features_poc.py \
  --input-dir scripts/poc_images \
  --write-db \
  --table-name user_face_features
```
