# 백엔드 기능 설계 (신규 추가)

기존 Phase 0/1 구현(매칭 + 크리처 생성)에 추가되는 기능 설계입니다.

| 파일 | 기능 | 구현 단계 |
|------|------|----------|
| [01_auth.md](./01_auth.md) | 인증 (회원가입/로그인/소셜/JWT) | F2 예정 |
| [02_users.md](./02_users.md) | 사용자 관리 (프로필 편집/비밀번호/탈퇴) | F3 예정 |
| [03_creatures_extensions.md](./03_creatures_extensions.md) | 크리처 확장 (이름편집/공개비공개/좋아요) | F2~F3 예정 |
| [04_comments.md](./04_comments.md) | 댓글 | F3 예정 |
| [05_plaza_websocket.md](./05_plaza_websocket.md) | 광장 WebSocket (멀티플레이어 + 채팅) | F3 예정 |

## DB 변경 요약

| 작업 | 내용 |
|------|------|
| 신규 테이블 | `users`, `likes`, `comments` |
| 기존 테이블 수정 | `creatures` — `is_public`, `name` 컬럼 추가 |
| `users` 컬럼 | `dark_mode`, `font_size` 추가 |

## 기존 구현 (Phase 0/1)

- `POST /match/face` — 얼굴 이미지 → TOP-3 포켓몬 매칭
- `POST /creatures` — 크리처 생성 (Veo 영상 생성 트리거)
- `GET /creatures/{id}/status` — 생성 상태 폴링
- `GET /health` — 서버 헬스 체크
