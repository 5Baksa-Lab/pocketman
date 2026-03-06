# common_rule 사용 가이드

이 디렉토리는 **어떤 생성형 AI(Claude/Codex/기타)**를 사용하더라도 파트별로 동일한 품질 기준을 적용하기 위한 컨텍스트 모음입니다.

---

## 1. 사용 순서

1. 작업 파트에 해당하는 컨텍스트 파일 1개를 선택한다.
2. 선택한 컨텍스트를 AI 프롬프트 상단에 그대로 붙여넣는다.
3. `docs/develop_rule`의 규칙과 함께 실행한다.
4. Stage 종료 시 개발일지를 반드시 남긴다.

---

## 2. 파일 매핑

| 작업 파트 | 컨텍스트 파일 |
|---|---|
| Frontend | `frontend_context.md` |
| Backend | `backend_context.md` |
| MLOps/Data | `mlops_context.md` |
| PM | `pm_context.md` |
| DevOps/QA | `devops_qa_context.md` |

---

## 3. 프롬프트 기본 조합

아래 순서로 AI에게 제공한다.

1. `docs/common_rule/<파트>_context.md`
2. `docs/develop_rule/01_global_rules.md`
3. `docs/develop_rule/02_ai_coding_rules.md`
4. 현재 Stage 목표/범위

---

## 4. 주의사항

- 파트 컨텍스트는 동시에 여러 개를 섞지 않는다. (주 역할 1개만)
- 교차 파트 작업이 필요한 경우, 주 파트 컨텍스트를 기준으로 하되 인터페이스 변경은 PM 승인 후 진행한다.
- 컨텍스트가 규칙을 대체하지 않는다. (실행 규칙은 `develop_rule`이 최우선)
