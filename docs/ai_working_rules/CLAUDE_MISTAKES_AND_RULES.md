# Claude AI 반복 실수 방지 규칙

> **이 문서는 Claude가 pocketman-dev-su 프로젝트에서 실제로 저지른 실수들을 기록하고,
> 새 컨텍스트를 열 때마다 같은 실수를 반복하지 않기 위한 자기 규칙이다.**
> 새 세션 시작 시 반드시 이 파일을 읽고 작업에 임한다.

---

## 0. 세션 시작 시 필수 체크리스트

새 컨텍스트(세션)에서 작업을 시작할 때 반드시 아래 순서를 지킨다.

```
[ ] 1. 이 파일(CLAUDE_MISTAKES_AND_RULES.md) 읽기
[ ] 2. docs/develop_rule/00_pre_work_protocol.md 읽기
[ ] 3. docs/develop_rule/01_global_rules.md 읽기
[ ] 4. docs/common_rule/<파트>_context.md 읽기
[ ] 5. 실제 파일 구조 직접 탐색 (compact 요약에만 의존 금지)
[ ] 6. 관련 기획 문서 직접 확인 후 작업 착수
```

컴팩트 요약(이전 대화 요약)은 참고용이며, 실제 코드/문서의 현재 상태와 다를 수 있다.
**코드와 문서는 항상 직접 읽어서 확인한다.**

---

## 1. 프로토콜 위반 (가장 중요)

### 실수 1-A: DB 마이그레이션을 프로토콜 없이 직접 적용
- **사건**: 2026-03-13, 마이그레이션 002~005를 `00_pre_work_protocol.md` 없이 Railway DB에 바로 적용
- **계획 보고 → 동의 → 3 질문 → 작업** 순서 전혀 없이 진행
- **영향**: 사용자가 직접 지적 → 롤백 → 재작업 발생

**규칙**: `00_pre_work_protocol.md`의 Step 1~4는 **코드 파일 수정 1줄, DB 적용 1회** 어느 것도 예외 없다.

### 실수 1-B: "동의합니다." 이외 답변을 동의로 간주
- "알겠습니다", "진행해주세요" 등은 동의가 아니다
- **"동의합니다."** 정확히 이 문구를 받아야만 작업 진행

### 실수 1-C: 코드 리뷰 요청 형식 누락/축약
- 리뷰가 점점 짧아지는 경향 반복 확인됨
- 반드시 `00_pre_work_protocol.md` Step 7 형식 그대로 작성:

```
[코드 리뷰 요청]

변경 파일 목록:
  - 파일경로 (변경 내용 한 줄 요약)

핵심 변경 내용:
  변경 전/후 코드 비교 또는 요약

확인 요청 사항:
  - 로직이 의도대로 동작하는지
  - 예상치 못한 부작용이 있는지
  - 더 나은 접근 방식이 있는지

잔여 리스크:
  이번 작업 후 남아 있는 알려진 리스크

개발일지 경로:
  docs/development_logs/.../DEVLOG.md
```

---

## 2. 코드 탐색 누락

### 실수 2-A: 컴포넌트 export 이름 확인 안 함
- **사건**: `Badge` import → 실제 export는 `TypeBadge` → 빌드 실패
- **사건**: `onSave` prop 사용 → 실제 prop은 `onSaved` → 빌드 실패
- **원인**: 파일을 직접 읽지 않고 이름을 추정

**규칙**: 컴포넌트를 import/prop으로 연결하기 전에 해당 파일을 직접 Read한다.

### 실수 2-B: API 스펙 수치를 문서 간 교차 확인 안 함
- **사건**: `04_api_alignment_matrix.md`에 댓글 300자 → DB는 VARCHAR(100)
- **원인**: 기획서 원본(`10_creatures_detail.md`)과 API 매트릭스를 동시에 보지 않음

**규칙**: 길이 제한, 타입, 열거값이 있는 필드는 반드시 **기획서 원본 ↔ DB 스키마 ↔ API 문서** 3곳을 교차 확인한다.

### 실수 2-C: 이전 컴팩트 요약에만 의존
- 컴팩트 요약의 파일 경로, 코드 내용은 이미 수정되었을 수 있다
- **반드시** 실제 파일을 Read 도구로 읽어서 현재 상태를 확인한다

---

## 3. DB 마이그레이션 규칙

### 실수 3-A: 기존 마이그레이션 파일 내용 수정으로 정책 변경 시도
- **사건**: `002` ON DELETE SET NULL → CASCADE 변경을 파일 수정으로만 처리
- **사건**: `005` CHECK 제약 누락을 파일 수정으로만 처리
- **문제**: 이미 적용된 DB에서 `ADD COLUMN IF NOT EXISTS`는 컬럼 존재 시 스킵 → 정책 변경 미적용

**규칙**: 이미 적용된 마이그레이션의 정책·제약 변경은 **새 forward migration 파일(006_*, 007_*)** 로만 처리한다.
패턴: `DROP CONSTRAINT IF EXISTS → ADD CONSTRAINT`

### 실수 3-B: 멱등성 과장 서술
- `IF NOT EXISTS` / `IF EXISTS`는 컬럼·테이블·인덱스 **생성** 멱등성만 보장한다
- FK 타입(CASCADE/SET NULL), CHECK 제약 내용 변경은 이것으로 보장되지 않는다
- DEVLOG에 "멱등성 보장"이라고 쓸 때는 반드시 범위를 명시한다

### 실수 3-C: 마이그레이션 파일 경로 표기 불일치
- 올바른 경로: `backend/migrations/xxx.sql` (프로젝트 루트 기준)
- 잘못된 표기: `migrations/xxx.sql` (backend 디렉토리 기준)
- 문서 및 DEVLOG에 일관되게 `backend/migrations/` 접두사를 붙인다

---

## 4. 빌드 테스트 규칙

### 실수 4-A: lint 테스트 누락
- `npm run build`만 실행하고 `npm run lint`를 빠뜨리는 경우 발생
- `00_pre_work_protocol.md` Step 5 기준: **build + lint 모두 통과**해야 완료

**프론트엔드 빌드 완료 기준:**
```bash
npm run build   # ✅ 빌드 오류 없음
npm run lint    # ✅ ESLint 오류 없음
```

**백엔드 빌드 완료 기준:**
```bash
cd backend && ../.venv/bin/python -c "from app.main import app; print('BACKEND OK')"
```
- 반드시 `cd backend` 후 실행하거나 절대 경로 사용 (루트에서 실행 시 `No module named 'app'` 오류)

### 실수 4-B: 작업 디렉토리 미확인으로 상대 경로 오류
- psql, python 등 실행 시 상대 경로 사용 → "No such file" 오류
- **규칙**: Bash 명령에서 파일 경로는 항상 절대 경로(`/Users/sups/Desktop/...`)를 사용하거나, 현재 디렉토리를 먼저 확인한다

---

## 5. 문서화 규칙

### 실수 5-A: DEVLOG 상단 범위와 하단 표의 파일 경로 불일치
- 표는 수정했지만 상단 범위 설명은 구버전 경로 그대로인 경우 발생
- DEVLOG 수정 시 모든 섹션의 파일 경로를 동시에 일괄 수정한다

### 실수 5-B: 개발일지를 빌드 테스트 전에 작성
- 빌드 실패 상태에서 개발일지 작성 → 내용이 부정확해짐
- 순서: **코드 → 빌드 성공 → 개발일지 → 코드 리뷰 요청**

### 실수 5-C: 개발일지 미작성 상태로 다음 Stage 준비
- `03_stage_completion_and_devlog.md` 4.1 강제 규칙: 개발일지 없는 Stage 종료 보고는 무효
- Stage 완료 선언 전에 반드시 DEVLOG 파일이 존재해야 한다

---

## 6. 아키텍처 규칙 (Backend)

### 실수 6-A: 계층 위반 가능성 미검토
- `router → domain → repository → adapter` 4계층 구조
- router에서 DB 직접 조작 금지 / domain에서 SQL 직접 작성 금지
- 새 코드 작성 시 항상 어느 계층인지 확인 후 작성

### 실수 6-B: FastAPI 라우트 순서 위반
- Static route(`/creatures/public`, `/creatures/my`, `/creatures/liked`)는 반드시 dynamic route(`/creatures/{creature_id}`) **앞에** 등록
- 순서 위반 시 `"my"`, `"liked"` 문자열이 creature_id로 파싱되어 404 발생

---

## 7. Frontend 규칙

### 실수 7-A: lib/types.ts에 없는 타입을 인라인 정의
- `frontend_context.md` 명시: "lib/types.ts에 없는 타입을 인라인으로 정의하지 않는다"
- 새 타입 필요 시 먼저 `lib/types.ts`에 추가한 후 사용

### 실수 7-B: 하드코딩 API URL
- 환경변수 `NEXT_PUBLIC_API_BASE_URL`만 사용
- 코드 내 `http://localhost:8000` 직접 사용 금지

### 실수 7-C: Toast/UI 컴포넌트 prop 미확인
- 컴포넌트 사용 전 해당 파일을 Read하여 실제 prop 이름/타입 확인
- 자주 틀린 사례: `className` prop 없는 컴포넌트, `onSave` vs `onSaved`

---

## 8. 다음 Stage 확인 방법

새 컨텍스트에서 "다음에 무엇을 해야 하나?"를 판단하는 순서:

```
1. docs/development_logs/<파트>/stage-*/DEVLOG.md 목록 확인
   → 가장 최근 완료된 Stage 파악

2. docs/기획/프론트엔드/implementation_strategy/03_stage_f3_share_feed.md 읽기
   → F3-1 완료 → F3-2 (Phaser 단독 플레이어) → F3-3 (Socket.io 멀티) 순서

3. docs/기획/v5_파트별_개발_실행계획_상세.md 읽기
   → 전체 Phase 로드맵 확인

4. 현재 프론트엔드/백엔드 파일 실제 탐색
   → 기구현 여부 코드로 직접 검증
```

**현재 (2026-03-13) 기준 완료된 Stage:**
- backend: b1, b2, b3, b4, b5-f3-migrations, b5-social-apis
- frontend: f1, f2, f3-share-feed, f3-1-creature-detail-my
- mlops: m1, m2, m3
- pm-devops: p1, p2, p3

**다음 대기 중인 Stage:**
- **frontend F3-2**: Plaza Phaser.js 맵 + 단독 플레이어 이동
- **frontend F3-3**: Socket.io 멀티플레이어 (F3-2 이후)

---

## 9. 이 문서 업데이트 규칙

- 새로운 실수가 발생하면 **즉시** 이 파일에 추가한다
- 섹션 번호는 기존 번호를 유지하고, 실수는 번호 아래 추가
- 날짜와 사건 내용을 간결하게 기록한다

마지막 업데이트: 2026-03-13
