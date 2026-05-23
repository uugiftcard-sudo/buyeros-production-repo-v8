-- ============================================================
-- BuyerOS Supabase Audit Query (read-only)
-- ============================================================
-- 點用:
--   1. Supabase Studio → SQL Editor → New query
--   2. 全部 paste 入去
--   3. RUN
--   4. 每一個 result panel 都 click「Download CSV」or screenshot
--   5. 8 個 result 全部攞畀 Claude
--
-- 純 read-only，唔會改 schema / data。
-- ============================================================


-- ============================================================
-- A. Tables overview (size, row count, RLS status)
-- ============================================================
SELECT
  c.relname AS table_name,
  pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
  c.reltuples::bigint AS estimated_rows,
  c.relrowsecurity AS rls_enabled,
  CASE WHEN c.relrowsecurity AND EXISTS (
    SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid
  ) THEN 'YES'
  WHEN c.relrowsecurity THEN '⚠️ RLS on but NO POLICY (= deny all)'
  ELSE '🚨 NO RLS'
  END AS rls_status,
  obj_description(c.oid, 'pg_class') AS comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY pg_total_relation_size(c.oid) DESC;


-- ============================================================
-- B. Columns of every table
-- ============================================================
SELECT
  table_name,
  ordinal_position AS pos,
  column_name,
  data_type,
  CASE WHEN character_maximum_length IS NOT NULL
       THEN '(' || character_maximum_length || ')' ELSE '' END AS len,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;


-- ============================================================
-- C. Foreign key relations (point relationships between tables)
-- ============================================================
SELECT
  tc.table_name AS from_table,
  kcu.column_name AS from_column,
  ccu.table_name AS to_table,
  ccu.column_name AS to_column,
  rc.update_rule,
  rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints rc
  ON rc.constraint_name = tc.constraint_name
 AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY from_table, from_column;


-- ============================================================
-- D. RLS policies (邊張 table 有邊條 policy)
-- ============================================================
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd AS command,
  qual AS using_expression,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;


-- ============================================================
-- E. Triggers (有冇 audit-style trigger？)
-- ============================================================
SELECT
  event_object_table AS table_name,
  trigger_name,
  action_timing,
  string_agg(event_manipulation, ', ') AS events,
  action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public'
GROUP BY event_object_table, trigger_name, action_timing, action_statement
ORDER BY event_object_table, trigger_name;


-- ============================================================
-- F. Functions / stored procedures
-- ============================================================
SELECT
  n.nspname AS schema,
  p.proname AS function_name,
  pg_get_function_arguments(p.oid) AS args,
  pg_get_function_result(p.oid) AS returns,
  CASE p.prokind
    WHEN 'f' THEN 'function'
    WHEN 'p' THEN 'procedure'
    WHEN 'a' THEN 'aggregate'
    WHEN 'w' THEN 'window'
  END AS kind,
  l.lanname AS language
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
JOIN pg_language l ON l.oid = p.prolang
WHERE n.nspname = 'public'
ORDER BY p.proname;


-- ============================================================
-- G. Views (報表 view？)
-- ============================================================
SELECT
  table_name AS view_name,
  view_definition
FROM information_schema.views
WHERE table_schema = 'public'
ORDER BY table_name;


-- ============================================================
-- H. Extensions installed (pg_cron / pgcrypto / vault 等等)
-- ============================================================
SELECT
  extname AS extension,
  extversion AS version,
  nspname AS schema
FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace
ORDER BY extname;


-- ============================================================
-- I. Cron jobs (如果裝咗 pg_cron)
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    RAISE NOTICE 'pg_cron installed — see cron.job table';
  ELSE
    RAISE NOTICE 'pg_cron not installed';
  END IF;
END $$;

-- 如果 pg_cron 有裝，呢條會出 rows:
SELECT jobid, schedule, command, active, jobname
FROM cron.job
WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron');


-- ============================================================
-- J. Auth users count (Supabase auth)
-- ============================================================
SELECT
  COUNT(*) AS total_users,
  COUNT(*) FILTER (WHERE last_sign_in_at > NOW() - INTERVAL '30 days') AS active_30d,
  COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') AS new_30d,
  COUNT(DISTINCT raw_app_meta_data->>'provider') AS distinct_providers
FROM auth.users;

-- 同時列 providers
SELECT
  raw_app_meta_data->>'provider' AS provider,
  COUNT(*) AS user_count
FROM auth.users
GROUP BY raw_app_meta_data->>'provider'
ORDER BY user_count DESC;


-- ============================================================
-- K. Storage buckets + size
-- ============================================================
SELECT
  b.name AS bucket,
  b.public,
  b.created_at,
  COUNT(o.id) AS object_count,
  pg_size_pretty(COALESCE(SUM((o.metadata->>'size')::bigint), 0)) AS total_size
FROM storage.buckets b
LEFT JOIN storage.objects o ON o.bucket_id = b.id
GROUP BY b.id, b.name, b.public, b.created_at
ORDER BY b.name;


-- ============================================================
-- L. Storage policies (RLS on storage.objects)
-- ============================================================
SELECT
  policyname,
  permissive,
  roles,
  cmd AS command,
  qual AS using_expression
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
ORDER BY policyname;


-- ============================================================
-- DONE — 12 個 result set 全部 copy / screenshot 畀 Claude
-- ============================================================
