# Stage 종료 및 개발일지 규칙

이 문서는 "한 파트의 한 단계(Stage)" 완료 시 반드시 수행해야 하는 절차를 정의합니다.

---

## 1. Stage 완료 판정 조건

아래 4개를 모두 만족해야 Stage 완료로 인정한다.

1. Stage 목표 기능 구현 완료
2. 테스트/검증 수행 및 결과 기록
3. 리스크/한계 명시
4. 개발일지 파일 생성 완료

---

## 2. 개발일지 생성 규칙

## 2.1 경로 규칙

개발일지는 아래 경로에 생성한다.

`docs/development_logs/<part>/stage-<stage>/DEVLOG.md`

예시:
- `docs/development_logs/frontend/stage-f1-upload-top3/DEVLOG.md`
- `docs/development_logs/backend/stage-b2-match-generate/DEVLOG.md`
- `docs/development_logs/mlops/stage-m2-vectorize/DEVLOG.md`

## 2.2 파일 생성 방식

1. 기본은 템플릿 복사 사용: `templates/DEVLOG_TEMPLATE.md`
2. 또는 스크립트 사용:

```bash
bash docs/develop_rule/scripts/init_stage_devlog.sh \
  --part backend \
  --stage b1-core-mock \
  --owner "김현섭"
```

## 2.3 작성 필수 항목

1. 목표/범위
2. 구현 상세 (핵심 로직)
3. 변경 파일 목록
4. 테스트 및 검증 결과
5. 이슈/리스크/미해결 항목
6. 다음 Stage 인수인계 내용
7. AI 활용 기록 (프롬프트/출력 요약)

---

## 3. Stage 종료 체크 절차

1. `checklists/STAGE_DONE_CHECKLIST.md`를 완료한다.
2. 체크리스트 완료 후 개발일지를 작성한다.
3. PM 또는 파트 리드가 개발일지를 리뷰한다.
4. 리뷰 승인 이후에만 다음 Stage로 이동한다.

---

## 4. 강제 규칙

1. 개발일지 없는 Stage 종료 보고는 무효 처리한다.
2. 개발일지에 테스트 증빙이 없으면 재작성한다.
3. 다음 Stage 착수 PR에는 이전 Stage 개발일지 경로를 반드시 포함한다.
