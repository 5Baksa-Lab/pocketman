-- Migration 006: 제약 조건 정정 (002/005 초기 적용분 보완)
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/006_fix_constraints.sql
--
-- 배경:
--   002 초기본: creatures.user_id FK가 ON DELETE SET NULL → CASCADE로 정정 (기획서 11_my.md:114)
--   005 초기본: users.font_size에 CHECK 제약 누락 → (14, 16, 18) 제한 추가 (기획서 11_my.md:94-96)
--
-- 멱등성: DROP IF EXISTS → ADD 패턴으로 중복 실행 안전

-- [1] creatures.user_id FK: SET NULL → CASCADE 정정
ALTER TABLE creatures
  DROP CONSTRAINT IF EXISTS creatures_user_id_fkey;

ALTER TABLE creatures
  ADD CONSTRAINT creatures_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- [2] users.font_size CHECK 제약 추가 (14px / 16px / 18px 3단계)
ALTER TABLE users
  DROP CONSTRAINT IF EXISTS chk_font_size;

ALTER TABLE users
  ADD CONSTRAINT chk_font_size
    CHECK (font_size IN (14, 16, 18));
