-- =============================================================================
-- Pokéman Docker 초기화: 마이그레이션 001~006 통합
-- =============================================================================

-- Migration 001: users
CREATE TABLE IF NOT EXISTS users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    nickname      VARCHAR(50)  NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- Migration 002: creatures.user_id
ALTER TABLE creatures ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_creatures_user_id ON creatures (user_id);

-- Migration 003: likes
CREATE TABLE IF NOT EXISTS likes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    creature_id UUID        NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, creature_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_creature_id ON likes (creature_id);
CREATE INDEX IF NOT EXISTS idx_likes_user_id     ON likes (user_id);

-- Migration 004: comments
CREATE TABLE IF NOT EXISTS comments (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    creature_id UUID         NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content     VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_comments_creature_id_created ON comments (creature_id, created_at DESC);

-- Migration 005: users profile columns
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS bio                VARCHAR(100),
  ADD COLUMN IF NOT EXISTS avatar_creature_id UUID REFERENCES creatures(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS dark_mode          BOOLEAN  NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS font_size          SMALLINT NOT NULL DEFAULT 16;

-- Migration 006: fix constraints
ALTER TABLE creatures DROP CONSTRAINT IF EXISTS creatures_user_id_fkey;
ALTER TABLE creatures ADD CONSTRAINT creatures_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_font_size;
ALTER TABLE users ADD CONSTRAINT chk_font_size CHECK (font_size IN (14, 16, 18));
