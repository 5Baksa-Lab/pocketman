# Pocketman Frontend (Next.js)

## 디렉토리 목적
- 이 디렉토리는 원본 `pocketman-dev-su`를 직접 건드리지 않고 UI/UX를 실험하기 위한 프로토타입 샌드박스입니다.
- 핵심 목표는 Pocketman의 랜딩과 브랜드 경험을 `Neo-Retro Pokedex` 방향으로 재설계하는 것입니다.
- 상세 배경은 `DESIGN_REVISION_LOG.md`를 참고하세요.

## 구현 범위
- 업로드 -> Top-3 선택 -> 생성 진행 -> 결과/공유
- 광장 피드 목록 + 이모지 리액션
- 백엔드 실 API 연동 (`/api/v1/*`)

## 실행
```bash
cp .env.example .env.local
npm install
npm run dev
```

브라우저: `http://localhost:3000`

## 환경변수
- `NEXT_PUBLIC_API_BASE_URL` (기본값: `http://localhost:8000/api/v1`)

## 주요 API 사용
- `POST /match`
- `POST /creatures`
- `POST /creatures/{id}/generate`
- `GET /veo-jobs/{job_id}`
- `GET /creatures/public`
- `POST /creatures/{id}/reactions`
- `GET /creatures/{id}/reactions/summary`

## 참고
- 결과 화면의 이름 편집은 현재 프론트 상태/공유 텍스트 기준입니다.
- `광장 등록` 버튼은 현재 생성 결과를 공개 크리처로 추가 등록합니다.
