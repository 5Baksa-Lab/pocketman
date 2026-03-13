-- Migration 004: comments 테이블 생성
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/004_create_comments.sql

CREATE TABLE IF NOT EXISTS comments (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id UUID         NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content     VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- 최신순(ORDER BY created_at DESC) 조회 최적화를 위한 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_comments_creature_id_created ON comments (creature_id, created_at DESC);
