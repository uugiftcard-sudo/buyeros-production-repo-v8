-- ============================================================
-- P2/P3 Pre-Apply Check: transactions.type + refunds.status enum values
-- ============================================================
-- 複製以下全部貼入 Supabase Studio → SQL Editor → Run
-- 下載結果 CSV 或截圖，發給 AI
-- ============================================================


-- A. transactions 表：所有欄位 + CHECK constraint enum 值
SELECT
    'transactions' AS table_name,
    column_name,
    data_type,
    CASE WHEN character_maximum_length IS NOT NULL
         THEN '(' || character_maximum_length || ')' ELSE '' END AS len,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'transactions'
ORDER BY ordinal_position;


-- B. transactions.type 的所有可能值（從 CHECK constraint 反推）
SELECT
    conname                     AS constraint_name,
    pg_get_constraintdef(oid)  AS definition
FROM pg_constraint
WHERE conrelid = 'public.transactions'::regclass
  AND contype = 'c';


-- C. refunds 表：所有欄位
SELECT
    'refunds' AS table_name,
    column_name,
    data_type,
    CASE WHEN character_maximum_length IS NOT NULL
         THEN '(' || character_maximum_length || ')' ELSE '' END AS len,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'refunds'
ORDER BY ordinal_position;


-- D. refunds.status 的所有可能值
SELECT
    conname                     AS constraint_name,
    pg_get_constraintdef(oid)  AS definition
FROM pg_constraint
WHERE conrelid = 'public.refunds'::regclass
  AND contype = 'c';


-- E. Sample data（各 5 行）確認值
SELECT id, type, status, amount_cents, created_at
FROM transactions
ORDER BY created_at DESC
LIMIT 5;

SELECT id, status, amount_cents, created_at
FROM refunds
ORDER BY created_at DESC
LIMIT 5;


-- F. transactions.type 目前 actual 值（distinct）
SELECT DISTINCT type FROM transactions ORDER BY type;

-- G. refunds.status 目前 actual 值（distinct）
SELECT DISTINCT status FROM refunds ORDER BY status;
