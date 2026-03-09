# Pocketman Frontend (Next.js)

## 구현 범위
- 업로드 -> Top-3 선택 -> 생성 진행 -> 결과/공유
- 광장 피드 목록 + 이모지 리액션
- 백엔드 실 API 연동 (`/api/v1/*`)

## 실행
```bash
cd frontend
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
