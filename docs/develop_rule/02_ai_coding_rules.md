# Claude/Codex 공통 AI 코딩 규칙

## 1. AI 실행 전 필수 입력

AI에게 작업을 요청할 때 아래 4개를 항상 제공한다.

1. `docs/common_rule/<파트>_context.md`
2. `docs/develop_rule/01_global_rules.md`
3. `docs/develop_rule/03_stage_completion_and_devlog.md`
4. 현재 Stage 목표/범위/완료조건

## 2. AI 출력 형식 규칙

AI는 항상 아래 형식으로 응답해야 한다.

1. 변경 요약 (무엇을 바꿨는지)
2. 변경 파일 목록
3. 핵심 구현 상세
4. 테스트 결과
5. 남은 리스크
6. Stage 종료 시 개발일지 생성 여부

## 3. 구현 행동 규칙

1. 기존 코드 구조를 먼저 탐색한 뒤 수정한다.
2. 대규모 파일 생성보다 모듈 분리를 우선한다.
3. 임시 우회 코드(TODO, 하드코딩)를 남길 경우 이유와 제거 시점을 명시한다.
4. API/스키마 변경이 발생하면 영향 파일을 함께 수정한다.
5. 테스트를 실행하지 못하면 이유를 명시한다.

## 4. 금지 규칙

1. 라우터에서 직접 DB 조작 금지.
2. UI 컴포넌트 내부에서 직접 비즈니스 규칙 계산 금지.
3. 실패 분기 없는 외부 API 호출 금지.
4. 개발일지 누락 상태로 Stage 완료 선언 금지.

## 5. 프롬프트 권장 템플릿

```text
[ROLE CONTEXT]
(해당 common_rule 파일 내용)

[DEVELOP RULE]
(01_global_rules + 03_stage_completion_and_devlog 핵심)

[TASK]
- 파트: <frontend/backend/mlops/pm-devops>
- Stage: <예: f1-upload-top3>
- 목표:
- 완료 조건:

[OUTPUT FORMAT]
1) 변경 요약
2) 변경 파일
3) 테스트
4) 리스크
5) 개발일지 생성 경로
```
