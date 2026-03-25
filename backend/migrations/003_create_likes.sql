-- Migration 003: likes 테이블 생성
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/003_create_likes.sql

CREATE TABLE IF NOT EXISTS likes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creature_id UUID        NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, creature_id)
);

CREATE INDEX IF NOT EXISTS idx_likes_creature_id ON likes (creature_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id     ON likes (user_id);
