-- Migration 002: creatures 테이블에 user_id(소유자) 컬럼 추가
-- 적용 대상: Railway PostgreSQL
-- 적용 일시: 2026-03-13
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/002_add_user_id_to_creatures.sql
-- 비고: 기존 creatures는 user_id=NULL (익명 크리처 허용)
-- 비고: ON DELETE CASCADE — 유저 탈퇴 시 해당 유저의 크리처 전체 삭제 (기획서 11_my.md:114)

ALTER TABLE creatures
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_creatures_user_id ON creatures (user_id);
