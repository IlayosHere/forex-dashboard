-- Migration 003: Create Ilay user and reassign all trades/accounts to them
--
-- Works on both SQLite (dev) and PostgreSQL (prod).
--
-- What it does:
--   1. Inserts user 'Ilay' (bcrypt hash for password 'Rtgz5172'), is_admin=1
--      Idempotent: INSERT OR IGNORE / ON CONFLICT DO NOTHING.
--   2. Reassigns every existing trade.owner and account.owner to 'Ilay'.
--
-- IMPORTANT: also add Ilay to the AUTH_USERS secret/env so seed_users_from_env
-- keeps the user in sync on future cold starts. See the db-migrate skill.

-- SQLite variant (comment the PostgreSQL block and uncomment this for sqlite3):
-- INSERT OR IGNORE INTO users (id, username, password_hash, is_admin, created_at)
-- VALUES (
--   lower(hex(randomblob(16))),
--   'Ilay',
--   '$2b$12$wRfE/LBIkzQZTuVQv.ZvrO32VxOqK.FeYEZcVTqRYejSaUDSiPC7u',
--   1,
--   datetime('now')
-- );

-- PostgreSQL variant (default; works on Cloud SQL):
INSERT INTO users (id, username, password_hash, is_admin, created_at)
VALUES (
  gen_random_uuid()::text,
  'Ilay',
  '$2b$12$wRfE/LBIkzQZTuVQv.ZvrO32VxOqK.FeYEZcVTqRYejSaUDSiPC7u',
  TRUE,
  NOW()
)
ON CONFLICT (username) DO NOTHING;

-- Reassign ownership of trades/accounts that are still under 'admin' to Ilay.
-- Leaves rows owned by other real users untouched.
UPDATE trades   SET owner = 'Ilay' WHERE owner = 'admin';
UPDATE accounts SET owner = 'Ilay' WHERE owner = 'admin';
