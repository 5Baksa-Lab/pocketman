# Claude/Codex 공통 AI 코딩 규칙

## 0. 작업 시작 전 필수 프로토콜

**모든 작업은 `00_pre_work_protocol.md`를 먼저 따른다.**

순서 요약:
1. 계획 보고 (Phase/Stage/내용/이유/최선 근거)
2. 사용자로부터 "동의합니다." 수신
3. 착수 전 필수 질문 3가지 제시 및 답변 수신
4. 그 이후에만 실제 작업 시작

---

## 1. AI 실행 전 필수 입력

AI에게 작업을 요청할 때 아래 4개를 항상 제공한다.

1. `docs/common_rule/<파트>_context.md`
2. `docs/develop_rule/00_pre_work_protocol.md`
3. `docs/develop_rule/01_global_rules.md`
4. 현재 Stage 목표/범위/완료조건

## 2. AI 출력 형식 규칙

AI는 항상 아래 형식으로 응답해야 한다.

1. 변경 요약 (무엇을 바꿨는지)
2. 변경 파일 목록
3. 핵심 구현 상세
4. 테스트 결과 (또는 미실행 사유)
5. 남은 리스크
6. Stage 종료 시 개발일지 생성 여부

## 3. 구현 행동 규칙

1. 기존 코드 구조를 먼저 탐색한 뒤 수정한다.
2. 대규모 파일 생성보다 모듈 분리를 우선한다.
3. 임시 우회 코드(TODO, 하드코딩)를 남길 경우 이유와 제거 시점을 명시한다.
4. API/스키마 변경이 발생하면 영향 파일을 함께 수정한다.
5. 테스트를 실행하지 못하면 이유를 명시한다.
6. 28D 벡터 구조를 변경할 때는 `scripts/shared/feature_mapping.py`를 먼저 수정하고 Backend `adapter/cv_adapter.py`도 함께 갱신한다.

## 4. 금지 규칙

1. `router`에서 직접 DB 조작 금지.
2. `domain`에서 직접 SQL 작성 금지 (`repository`를 통해서만).
3. UI 컴포넌트 내부에서 직접 비즈니스 규칙 계산 금지.
4. 실패 분기 없는 외부 API 호출 금지 (Gemini/Imagen/Veo 모두 해당).
5. 개발일지 누락 상태로 Stage 완료 선언 금지.
6. `scripts/shared/feature_mapping.py` 변경 없이 벡터 차원 수 변경 금지.

## 5. 프롬프트 권장 템플릿

```text
[ROLE CONTEXT]
(docs/common_rule/<파트>_context.md 내용 전체)

[DEVELOP RULE]
(docs/develop_rule/01_global_rules.md 핵심)
(docs/develop_rule/03_stage_completion_and_devlog.md 핵심)

[CURRENT STATE]
- 관련 파일 구조:
- 기존 코드 동작 방식:
- 알려진 기술부채:

[TASK]
- 파트: <frontend | backend | mlops | pm-devops>
- Stage: <예: b3-video-feed-stabilize>
- 목표:
- 완료 조건:
- 제외 범위:

[OUTPUT FORMAT]
1) 변경 요약
2) 변경 파일 목록
3) 핵심 구현 상세
4) 테스트 결과 또는 미실행 사유
5) 남은 리스크
6) 개발일지 생성 경로
```
