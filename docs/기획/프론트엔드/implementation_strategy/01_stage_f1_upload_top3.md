# Stage F1 구현전략: Upload + Top3

> **상태: 완료 (2026-03-11)**
> F1 DEVLOG: `docs/development_logs/frontend/stage-f1-upload-top3/DEVLOG.md`
> 빌드 통과 확인 (8개 라우트, ESLint 0 errors)

---

## 1. Stage 목표

- 사용자가 서비스에 처음 진입해서 포켓몬 Top3 매칭 결과를 확인할 때까지의 핵심 여정을 완성한다.
- "업로드 성공 경험"과 "매칭 결과 신뢰감"을 확보한다.

핵심 성공 지표:
- 업로드 시작 대비 `/match` 도달률
- 업로드 실패 후 재시도 성공률
- `/match`에서 이탈률

---

## 2. 포함/제외 범위

포함 라우트:
- `/intro` ✅ 완료
- `/` ✅ 완료
- `/upload` ✅ 완료
- `/match` ✅ 스캐폴딩 완료 (Full 카드 디자인은 F2에서 구현)

제외 라우트:
- `/generate/[id]`
- `/result/[id]`
- `/login`, `/signup`
- `/plaza`, `/creatures/[id]`, `/my*`

---

## 3. 사용자 플로우

1. 사용자가 `/intro` 또는 `/`로 진입
2. 랜딩 CTA를 통해 `/upload` 이동
3. 이미지 업로드/검증 후 매칭 요청
4. 성공 시 sessionStorage 저장 → `/match`에서 Top3 확인
5. 실패 시 같은 페이지에서 즉시 복구(재업로드)

---

## 4. 페이지별 UI 구현 단계

### 4.1 `/intro` ✅ 완료

목표:
- 브랜드 첫 인상을 제공하고 랜딩으로 자연스럽게 연결

UI 구조:
- Desktop/Tablet/Mobile 공통 풀스크린 (Header/Nav 없음)
- 우상단 `Skip` 버튼 → `/` 즉시 이동
- 중앙 시네마틱 영역 + 하단 CTA

디자인 상세:
- 배경: 검정 (`#000000`)
- 포켓몬 5종 랜덤 노출 — ID: 25(피카츄), 4(파이리), 7(꼬부기), 1(이상해씨), 150(뮤츠)
- 이미지 소스: `https://www.serebii.net/pokemongo/pokemon/{id:03d}.png`
- 5단계 시퀀스 (클릭 전환, 자동 진행 없음):
  1. 포켓몬 실루엣 등장 (filter: brightness(0))
  2. 스캔 라인 애니메이션 (위→아래 sweep, 0.8s)
  3. 실루엣 → 이미지 reveal (filter: brightness(1), 0.6s)
  4. 텍스트 등장: "당신과 닮은 포켓몬이 있습니다"
  5. CTA 버튼: "시작하기 →" → `/` 이동

상태:
- `step1` | `step2` | `step3` | `step4` | `step5` | `skipped`

완료 기준:
- 단계 스킵/완료 시 이동이 항상 일관적
- 애니메이션 실패 시에도 CTA 접근 가능
- `prefers-reduced-motion`: 애니메이션 생략, 즉시 step5

---

### 4.2 `/` (랜딩) ✅ 완료

목표:
- 서비스 가치 설명 + `/upload` 전환 유도

UI 구조:
```
HERO 섹션 (다크 배경 #1a1a1a)
  - 좌: 피카츄 이미지 (serebii.net)
  - 우: 샘플 얼굴 사진 (Unsplash)
  - Ghost text: 배경에 "POKEMON" 대문자 (opacity 0.05)

ANALYSIS 섹션
  - "얼굴을 분석합니다" + 아이콘 + 설명

MATCHING 섹션
  - "386마리 포켓몬과 비교합니다" + 아이콘 + 설명

CREATION 섹션
  - "나만의 크리처가 탄생합니다" + 아이콘 + 설명

CTA 섹션
  - [지금 시작하기] 버튼 → /upload

SAMPLE 섹션
  - 공개 크리처 6개 그리드
  - API 실패 시 섹션 전체 숨김 (silent fail)
```

상태:
- `loadingSamples` | `samplesReady` | `samplesHidden`

구현 단계:
1. 섹션별 레이아웃 골격 먼저 구현
2. Hero에 ghost text 레이어 추가
3. Intersection Observer로 섹션 진입 애니메이션 연결 (fadeIn + slideUp)
4. `GET /api/v1/creatures/public?limit=6` 요청/렌더링
5. 샘플 API 실패 시 섹션 숨김 처리

완료 기준:
- 첫 스크린에서 CTA 명확히 노출
- 샘플 섹션 실패가 전체 레이아웃을 깨지 않음

---

### 4.3 `/upload` ✅ 완료

목표:
- 파일 검증/업로드/매칭 호출을 안정적으로 처리

UI 구조:
```
헤드라인: "당신과 닮은 포켓몬을 찾아드립니다"

DropZone:
  기본:       점선 테두리(#e0d5c0), 회색 업로드 아이콘
  drag over:  코랄(#f15946) 테두리 + 배경 틴트
  선택됨:     미리보기 썸네일 + [분석 시작] 버튼
  분석 중:    Spinner + "포켓몬을 찾는 중..."
  에러:       빨간 테두리 + 인라인 에러

하단:
  "샘플 사진으로 체험하기" (ghost 버튼)
  "🔒 사진은 분석 후 즉시 삭제됩니다"
```

상태:
- `idle` | `dragOver` | `selected` | `validating` | `uploading` | `error`

구현 단계:
1. DropZone drag 이벤트 + 파일 선택 이벤트 통합
2. 클라이언트 검증 순서: MIME 타입 → 파일 크기(10MB) → 해상도(100×100px)
3. 검증 실패 메시지 매핑 (에러 코드표 참조)
4. `POST /api/v1/match` 호출 + 로딩 상태
5. 성공 시 `MatchResultStorage.save(data.top3)` → sessionStorage 저장 → `/match` 이동
6. 실패 시 에러 메시지 표시 + 재시도 가능 상태 복귀

완료 기준:
- 잘못된 파일은 서버 호출 없이 차단
- 업로드 중 중복 클릭 방지 (버튼 disabled)
- 실패 후 즉시 재업로드 가능

---

### 4.4 `/match` — F1: 스캐폴딩 완료, F2: 카드 완성

F1 완료 내용:
- sessionStorage 수신 확인 (DEVLOG 기준)
- `/upload` 리다이렉트 처리

F2에서 구현할 내용 (아래 F1 handoff 스펙 고정):

**davidkpiano 카드 디자인 명세 (F2 구현 기준):**
```
카드 구조:
  배경: 포켓몬 primary_type 기반 색상
       + 다이아몬드 패턴:
         repeating-linear-gradient(
           45deg,
           transparent, transparent 4px,
           rgba(0,0,0,0.08) 4px, rgba(0,0,0,0.08) 5px
         )

  좌측 패널 (.pokemon-image):
    - 이미지 소스: https://www.serebii.net/pokemongo/pokemon/{pokemon_id:03d}.png
    - 라디얼 글로우: radial-gradient(circle at 50% 60%, rgba(255,255,255,0.3), transparent 70%)
    - head 바운스: @keyframes 0%{translateY(0)} 50%{translateY(-8px)} 100%{translateY(0)}, 2s ease-in-out infinite

  우측 패널 (.dex, font-family: Lato):
    ◉ #{pokemon_id:03d}  {name_kr}   (letter-spacing: 0.2em)
    Type: <TypeBadge type={primary_type} />
    유사도: {(similarity * 100).toFixed(1)}%
    {reasons[0].label}  {reasons[1].label}
    [유사도 프로그레스바] ({similarity*100}%, 타입 색상)
    [이 포켓몬으로 시작하기] 버튼 (코랄 #f15946)
```

타입별 배경 색상표:
```
불꽃(fire):   #c97c4a
물(water):    #5b8fc9
전기(electric):#c9a93b
풀(grass):    #6aab4f
에스퍼(psychic):#9b8ec4
노말(normal): #a0a0a0
독(poison):   #9b5fc9
얼음(ice):    #7ac9c9
격투(fighting):#c94a4a
비행(flying): #7a9bc9
땅(ground):   #c9a96e
바위(rock):   #8a7f5c
벌레(bug):    #7aab4f
고스트(ghost): #5c4a7a
드래곤(dragon):#5c7ac9
강철(steel):  #8a9bab
악(dark):     #4a3a5c
페어리(fairy): #c97aab
```

TOP-3 배치:
- Desktop: 3열 가로 배치, 1위 `scale(1.05)` + "BEST MATCH" 뱃지
- Mobile: 세로 스택 (1위 맨 위)
- 선택 시: 선택 카드 scale-up, 나머지 opacity→0 (0.4s), 0.6s 후 API 호출

sessionStorage 데이터 스키마 (F2 handoff 고정):
```typescript
interface MatchResult {
  rank: number           // 1 | 2 | 3
  pokemon_id: number
  name_kr: string
  name_en: string
  primary_type: string
  secondary_type: string | null
  sprite_url: string | null  // serebii.net URL (백엔드 미제공 시 프론트 조합)
  similarity: number     // 0.0 ~ 1.0
  reasons: Array<{
    dimension: string
    label: string
    user_value: number
    pokemon_value: number
  }>
}
```

상태:
- `loadingFromSession` | `noSession` | `ready` | `selecting` | `creating`

완료 기준 (F2):
- 세션 유실 시 `/upload`로 즉시 복귀
- 결과 데이터 누락 필드 있어도 카드 렌더링 불깨짐
- 중복 클릭으로 duplicate 생성 요청 발생 안함

---

## 5. 공통 컴포넌트/모듈 계획

구현 완료:
- `PocketmanLogo` (Luckiest Guy + CSS multi-shadow)
- `DropZone`
- `Button` (primary/secondary/ghost, sm/md/lg)
- `Badge` (TypeBadge 포함)
- `Spinner`
- `Toast`
- `lib/storage.ts` (MatchResultStorage)
- `lib/constants.ts` (MAX_FILE_SIZE, ACCEPTED_MIME_TYPES)

F2에서 추가:
- `PokemonCard` (davidkpiano 풀 디자인)
- `TypeBadge` (18개 타입 색상)

---

## 6. 상태 전이 모델

Upload 전이:
```
idle + 파일입력          → validating
validating + 통과        → uploading
validating + 실패        → error (에러 메시지 표시)
uploading + 성공(200)    → navigating(match)
uploading + 실패(4xx/5xx)→ error (재시도 가능)
```

Match 전이 (F2 handoff):
```
init + 마운트            → loadingFromSession
loadingFromSession + 있음 → ready
loadingFromSession + 없음 → noSession → redirect(/upload)
ready + 카드선택          → selecting
selecting + 0.6s          → creating (POST /api/v1/creatures)
creating + 성공           → navigate(/generate/{id})
creating + 실패           → ready (재선택 가능)
```

---

## 7. API 계약 (확정)

### POST `/api/v1/match`

요청:
```
Content-Type: multipart/form-data
body: { file: File }
```

성공 응답 (200):
```json
{
  "success": true,
  "data": {
    "top3": [
      {
        "rank": 1,
        "pokemon_id": 25,
        "name_kr": "피카츄",
        "name_en": "Pikachu",
        "primary_type": "electric",
        "secondary_type": null,
        "sprite_url": null,
        "similarity": 0.8923,
        "reasons": [
          { "dimension": "visual", "label": "큰 눈", "user_value": 0.8, "pokemon_value": 0.75 }
        ]
      }
    ]
  }
}
```

프론트 필수 필드: `rank`, `pokemon_id`, `name_kr`, `primary_type`, `similarity`, `reasons`

`sprite_url`이 null이면 프론트에서 serebii.net URL 조합:
```typescript
const getPokeGoImageUrl = (id: number) =>
  `https://www.serebii.net/pokemongo/pokemon/${String(id).padStart(3, '0')}.png`
```

실패 코드 → 사용자 메시지:
| error_code | HTTP | 사용자 메시지 |
|---|---|---|
| `UNSUPPORTED_MEDIA_TYPE` | 415 | JPG, PNG, WebP 파일만 업로드할 수 있어요 |
| `FILE_TOO_LARGE` | 413 | 파일 크기가 10MB를 초과해요 |
| `FACE_NOT_DETECTED` | 422 | 얼굴을 찾지 못했어요. 얼굴이 잘 보이는 사진을 사용해 주세요 |
| `MULTIPLE_FACES` | 422 | 얼굴이 2개 이상 감지됐어요. 혼자 찍은 사진을 사용해 주세요 |
| `LOW_QUALITY` | 422 | 이미지 화질이 너무 낮아요. 더 선명한 사진을 사용해 주세요 |
| `INTERNAL_ERROR` | 500 | 잠시 후 다시 시도해 주세요 |

재시도 가능 여부: 4xx → 즉시, 5xx → 3초 후

---

## 8. 예외/엣지케이스

1. HEIC/AVIF 파일 → MIME 체크에서 차단 (`image/heic` 미포함)
2. 해상도 100×100px 미만 → 클라이언트에서 `Image` 객체로 검증 후 차단
3. 네트워크 단절 중 업로드 버튼 연타 → `uploading` 상태 진입 시 버튼 disabled
4. 업로드 성공 직후 새로고침으로 세션 유실 → `/match` 접근 시 `/upload` 리다이렉트
5. Top3 중 `sprite_url` null → serebii.net fallback URL 적용
6. serebii.net 이미지 로드 실패 → 회색 포켓볼 placeholder

---

## 9. QA 체크포인트 (F1)

Happy path:
1. `/` → [지금 시작하기] → `/upload` → 유효 이미지 업로드 → `/match` 도달
2. Top3 카드 3개 모두 렌더링 (1위 강조)
3. `/intro` → skip → `/` 이동

Failure path:
1. HEIC 파일 업로드 → 즉시 에러 (서버 호출 없음)
2. 10MB 초과 → 즉시 에러 (서버 호출 없음)
3. 얼굴 없는 이미지 → FACE_NOT_DETECTED 메시지 표시

Recovery path:
1. 실패 후 다른 이미지로 즉시 재시도 → 성공
2. `/match` 세션 유실 → `/upload` 자동 복귀

---

## 10. 후속 백로그

| 항목 | 미루는 이유 | 예상 Stage | 선행조건 |
|------|-----------|-----------|---------|
| `/match` davidkpiano 카드 완성 | F2 핵심 구현 | F2 | PokeAPI 타입 정보 |
| 랜딩 parallax 고도화 | 핵심 플로우 우선 | F3 이후 | — |
| 인트로 5단계 고급 애니메이션 튜닝 | 현재 3단계로 작동 | F3 이후 | — |
| 샘플 섹션 skeleton loader | 현재 silent fail | F3 | — |
