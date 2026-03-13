-- Migration 005: users 테이블 프로필 컬럼 추가
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/005_add_users_columns.sql

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS bio                VARCHAR(100),
  ADD COLUMN IF NOT EXISTS avatar_creature_id UUID REFERENCES creatures(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS dark_mode          BOOLEAN  NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS font_size          SMALLINT NOT NULL DEFAULT 16
                                              CONSTRAINT chk_font_size CHECK (font_size IN (14, 16, 18));
