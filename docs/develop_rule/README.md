# develop_rule 사용 가이드

이 디렉토리는 실제 구현 시 따라야 하는 **강제 개발 규칙**입니다.

---

## 1. 적용 우선순위

1. `00_pre_work_protocol.md` (작업 착수 전 필수 프로토콜 — 최우선)
2. `01_global_rules.md` (전역 규칙)
3. `02_ai_coding_rules.md` (Claude/Codex 공통 실행 규칙)
4. `03_stage_completion_and_devlog.md` (단계 종료 규칙)
5. `checklists/STAGE_DONE_CHECKLIST.md` (종료 체크)
6. `templates/DEVLOG_TEMPLATE.md` (개발일지 템플릿)

---

## 2. 핵심 원칙

1. Stage 단위 개발
2. Stage 종료 시 개발일지 작성 의무
3. 개발일지 미작성 상태에서 다음 Stage 착수 금지

---

## 3. 개발일지 자동 생성

```bash
bash docs/develop_rule/scripts/init_stage_devlog.sh \
  --part frontend \
  --stage f1-upload-top3 \
  --owner "홍길동"
```

생성 경로:
`docs/development_logs/<part>/stage-<stage>/DEVLOG.md`
