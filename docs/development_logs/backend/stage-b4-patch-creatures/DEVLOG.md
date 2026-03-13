# Stage 개발일지

## 0) 기본 정보
- 파트: `backend`
- Stage: `b4-patch-creatures`
- 작성자: `sups`
- 작성일: `2026-03-13`
- 관련 이슈/PR: N/A

## 1) Stage 목표/범위
- 목표: `PATCH /api/v1/creatures/{id}` 엔드포인트 추가 — 이름 인라인 편집 및 광장 공개 전환 지원
- 이번 Stage에서 포함한 범위:
  - `CreaturePatchRequest` 스키마 추가 (name, is_public 2필드)
  - `patch_creature()` repository 함수 추가
  - `patch_creature_item()` domain service 함수 추가
  - `PATCH /creatures/{creature_id}` router 엔드포인트 추가
- 제외한 범위:
  - Ownership 검증 (user_id 미연결 상태 — F3에서 처리)
  - name/is_public 외 필드 수정

## 2) 구현 상세

### 2.1 핵심 설계/의사결정

**결정 1: partial update 방식**
- `name`, `is_public` 모두 Optional 필드로 선언
- 둘 다 None인 경우 (빈 body) → UPDATE 없이 현재 creature 그대로 200 반환 (no-op)
- 이유: 클라이언트가 실수로 빈 요청을 보냈을 때 데이터 손실 없이 안전하게 처리

**결정 2: 동적 SET 절 생성**
- None이 아닌 필드만 `SET name = %s`, `SET is_public = %s` 절에 포함
- 이유: 단일 PATCH로 name만, is_public만, 또는 둘 다 업데이트하는 3가지 케이스를 모두 처리
- `COALESCE` 미사용 — 명시적 조건 분기가 의도 명확

**결정 3: Ownership 미검증 (기술부채)**
- F2 MVP에서 `creatures` 테이블에 `user_id` 컬럼이 없으므로 소유권 검증 불가
- F3에서 `user_id` 컬럼 추가 후 `403 FORBIDDEN` 에러 연동 예정

**결정 4: 라우트 등록 위치**
- `GET /creatures/{creature_id}` 직후, `POST /creatures/{creature_id}/reactions` 직전에 등록
- `GET /creatures/public`이 이미 `GET /creatures/{id}` 앞에 있어 경로 충돌 없음
- `PATCH`는 HTTP method가 달라 `GET /creatures/{id}`와 충돌 없음

### 2.2 핵심 로직 설명

**patch_creature() — repository:**
- `fields`에 포함된 키만 SET 절에 포함
- `fields`가 비어 있으면 `get_creature_by_id()` 그대로 반환 (no-op)
- creature 없으면 None 반환 → service에서 404 처리

**patch_creature_item() — service:**
- `req.name`, `req.is_public` 중 None이 아닌 것만 `fields` dict에 담아 repository 전달
- `_normalize_creature_row()` 패턴으로 UUID → str 변환 (기존 코드 일관성 유지)

### 2.3 변경 파일 목록

- `backend/app/core/schemas.py`: `CreaturePatchRequest` 클래스 추가
- `backend/app/repository/creature_repository.py`: `patch_creature()` 함수 추가
- `backend/app/domain/creatures/creature_service.py`: import 추가 + `patch_creature_item()` 함수 추가
- `backend/app/api/v1/routers/creatures.py`: import 추가 + `PATCH /creatures/{creature_id}` 엔드포인트 추가

## 3) 테스트/검증

### 3.1 빌드 테스트

```bash
cd backend && ../.venv/bin/python -c "from app.main import app; print('OK')"
# → OK
```

### 3.2 라우트 등록 검증

```
{'POST'} /creatures
{'GET'}  /creatures/public
{'GET'}  /creatures/{creature_id}
{'PATCH'} /creatures/{creature_id}        ← 신규
{'POST'} /creatures/{creature_id}/reactions
{'GET'}  /creatures/{creature_id}/reactions/summary
```
순서 및 등록 정상 확인.

### 3.3 수동 실서버 검증
- USE_MOCK_AI=true 환경 미기동 (로컬 환경 미준비 상태)
- 빌드 테스트(import) 통과로 대체
- 실서버 연동 검증은 F2 프론트엔드 연동 시 함께 수행 예정

## 4) 이슈/리스크

| 항목 | 내용 | 대응 |
|------|------|------|
| Ownership 미검증 | user_id 없어 본인 크리처만 수정 강제 불가 | F3에서 user_id 컬럼 추가 후 403 연동 |
| 빈 body no-op | 클라이언트가 빈 요청 시 200 반환 (데이터 변경 없음) | 명세서에 no-op 동작 명시 완료 |

## 5) 다음 Stage 인수인계

- 다음 Stage: B-2 — Auth API 추가 (register/login/me) + users 테이블 migration
- 주의할 점:
  - `python-jose[cryptography]`, `passlib[bcrypt]` requirements.txt 추가 필요
  - Railway PostgreSQL에 `users` 테이블 `CREATE TABLE IF NOT EXISTS` migration 필요
  - `.env`에 `JWT_SECRET_KEY` 추가 필요
- 필요한 사전조건: Railway DB 접속 가능 상태

## 6) AI 활용 기록

- 사용한 AI: Claude Sonnet 4.6 (Claude Code)
- 역할: 전체 코드 작성 (B-4 PATCH 엔드포인트)
- 사람이 결정한 것: no-op 200 반환 방식, name+is_public 2필드 제한

## 7) 완료 체크

- [x] `CreaturePatchRequest` 스키마 추가
- [x] `patch_creature()` repository 함수 추가
- [x] `patch_creature_item()` service 함수 추가
- [x] `PATCH /creatures/{creature_id}` 엔드포인트 추가
- [x] 라우트 순서 검증 (public → {id} → PATCH {id} 순서 유지)
- [x] 빌드 테스트 통과 (`from app.main import app` OK)
- [x] 개발일지 작성
- [ ] PM/리드 리뷰 완료
