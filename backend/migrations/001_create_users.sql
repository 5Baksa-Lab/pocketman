-- Migration 001: users 테이블 생성
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/001_create_users.sql

CREATE TABLE IF NOT EXISTS users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    nickname      VARCHAR(50)  NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
