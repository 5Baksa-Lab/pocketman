-- Migration 007: creatures 테이블에 sprite_url 컬럼 추가
-- 적용 대상: Railway PostgreSQL
-- 실행 방법: psql $DATABASE_URL -f backend/migrations/007_add_sprite_url.sql
-- 멱등성: IF NOT EXISTS 패턴 사용

ALTER TABLE creatures
  ADD COLUMN IF NOT EXISTS sprite_url TEXT DEFAULT NULL;
