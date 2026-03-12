# 프론트엔드 구현전략 (Stage 기반)

## 목적
이 디렉토리는 `docs/기획/프론트엔드`의 페이지 설계를 실제 구현 가능한 단위로 재구성한 Stage 실행 문서 모음입니다.

핵심 목표:
- 페이지별 아이디어를 Stage 단위로 묶어 구현 순서를 고정한다.
- 각 Stage에서 "무엇을 먼저 만들고, 무엇을 나중에 미루는지"를 명확히 한다.
- API/상태/예외 케이스를 문서 단계에서 먼저 정렬해 개발 중 재작업을 줄인다.

---

## 문서 구성

1. `00_stage_playbook.md`
- Stage 문서를 작성/업데이트할 때 사용하는 공통 포맷
- 모든 Stage 문서의 기준 템플릿

2. `01_stage_f1_upload_top3.md`
- F1 구현전략
- 대상 라우트: `/intro`, `/`, `/upload`, `/match`

3. `02_stage_f2_result_generation.md`
- F2 구현전략
- 대상 라우트: `/match`(handoff), `/generate/[id]`, `/result/[id]`, `/login`, `/signup`

4. `03_stage_f3_share_feed.md`
- F3 구현전략
- 대상 라우트: `/plaza`, `/creatures/[id]`, `/my`, `/my/edit`, `/my/password`

5. `04_api_alignment_matrix.md`
- 기획 문서 API와 현재 구현 API 간 차이를 정렬한 매트릭스
- 선행 결정 항목 정리

6. `05_stage_qa_master_checklist.md`
- Stage별 QA 마스터 체크리스트
- 실패/지연/권한/빈데이터 시나리오 포함

---

## Stage 진행 순서

1. Stage F1
- 유입과 첫 가치 경험(업로드/매칭 Top3) 완성

2. Stage F2
- 생성/결과/인증을 연결해 핵심 퍼널을 완결

3. Stage F3
- 광장/상세/마이 기능으로 공유 및 계정 경험 확장

---

## 사용 방법

1. 해당 Stage 문서를 열고 범위(포함/제외)를 먼저 확인한다.
2. 페이지별 구현 단계를 순서대로 적용한다.
3. API 계약은 반드시 `04_api_alignment_matrix.md`에서 최신 상태를 확인한다.
4. QA는 `05_stage_qa_master_checklist.md` 기준으로 Stage 완료 전 점검한다.

---

## 업데이트 원칙

- 새 기능 추가 시 먼저 어느 Stage에 속하는지 정의한다.
- Stage 외 기능은 "후속 Stage 백로그" 섹션에만 기록한다.
- API가 변경되면 Stage 문서보다 먼저 `04_api_alignment_matrix.md`를 갱신한다.
