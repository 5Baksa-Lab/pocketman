# Stage 종료 및 개발일지 규칙

이 문서는 "한 파트의 한 단계(Stage)" 완료 시 반드시 수행해야 하는 절차를 정의합니다.

---

## 1. Stage 완료 판정 조건

아래 4개를 모두 만족해야 Stage 완료로 인정한다.

1. Stage 목표 기능 구현 완료
2. 테스트/검증 수행 및 결과 기록 (미실행 시 사유 명시)
3. 리스크/한계 명시
4. 개발일지 파일 생성 완료

---

## 2. 개발일지 생성 규칙

### 2.1 경로 규칙

개발일지는 아래 경로에 생성한다.

`docs/development_logs/<part>/stage-<stage>/DEVLOG.md`

예시:
- `docs/development_logs/frontend/stage-f1-upload-top3/DEVLOG.md`
- `docs/development_logs/backend/stage-b2-match-generate/DEVLOG.md`
- `docs/development_logs/mlops/stage-m2-vectorize/DEVLOG.md`
- `docs/development_logs/pm-devops/stage-p1-baseline/DEVLOG.md`

### 2.2 파일 생성 방식

1. 스크립트 사용 (권장):

```bash
bash docs/develop_rule/scripts/init_stage_devlog.sh \
  --part backend \
  --stage b1-core-mock \
  --owner "이름"
```

2. 또는 템플릿 직접 복사: `docs/develop_rule/templates/DEVLOG_TEMPLATE.md`

### 2.3 작성 필수 항목

1. 목표/범위
2. 구현 상세 (핵심 로직, 의사결정 이유)
3. 변경 파일 목록
4. 테스트 및 검증 결과
5. 이슈/리스크/미해결 항목
6. 다음 Stage 인수인계 내용
7. AI 활용 기록 (사용한 AI, 프롬프트 요약, 채택/수정 내용)

---

## 3. Stage 종료 체크 절차

1. `docs/develop_rule/checklists/STAGE_DONE_CHECKLIST.md`를 완료한다.
2. 체크리스트 완료 후 개발일지를 작성한다.
3. PM 또는 파트 리드가 개발일지를 리뷰한다.
4. 리뷰 승인 이후에만 다음 Stage로 이동한다.

---

## 4. 강제 규칙

1. 개발일지 없는 Stage 종료 보고는 무효 처리한다.
2. 개발일지에 테스트 증빙이 없으면 재작성한다.
3. 다음 Stage 착수 PR에는 이전 Stage 개발일지 경로를 반드시 포함한다.

---

## 5. 현재 정의된 Stage 목록

| 파트 | Stage ID | 설명 |
|---|---|---|
| frontend | f1-upload-top3 | 이미지 업로드 + 매칭 Top3 |
| frontend | f2-result-generation | 크리처 생성 결과 + Veo 폴링 |
| frontend | f3-share-feed | 광장 피드 + 공유 |
| backend | b1-core-mock | 4-layer 스캐폴드 + Mock 모드 |
| backend | b2-match-generate | pgvector 매칭 + 생성 파이프라인 |
| backend | b3-video-feed-stabilize | Veo Job 상태 머신 + 광장 피드 |
| mlops | m1-data-build | PokeAPI 수집 + Gemini 주석 |
| mlops | m2-vectorize | 28D 벡터 빌드 + DB 적재 |
| mlops | m3-runtime-cv | MediaPipe CV 추출 + PoC 검증 |
| pm-devops | p1-baseline | 스키마 확정 + Docker Compose |
| pm-devops | p2-cicd-quality | CI/CD 설계 + 의존성 매핑 |
| pm-devops | p3-release-demo | 배포 + 발표 환경 고정 |
