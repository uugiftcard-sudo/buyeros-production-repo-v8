-- ============================================================
-- BuyerOS Seed Data
-- 測試資料：買手對象系統演示 / 開發環境
-- ============================================================
-- 使用方式：
--   1. 在 Supabase Studio SQL Editor 執行
--   2. 或：npx supabase db seed --file supabase/seed.sql
--
-- ⚠️ 警告：這是測試資料，請在 DEV / STAGING 環境執行
-- 生產環境請先備份！
-- ============================================================

BEGIN;

-- ============================================================
-- Helper: 亂數生成 UUID（用於 FK 關係建立）
-- ============================================================

DO $$
DECLARE
    -- Buyers
    buyer_alice   UUID := gen_random_uuid();
    buyer_bob     UUID := gen_random_uuid();
    buyer_carol   UUID := gen_random_uuid();

    -- Customers
    cust_david    UUID := gen_random_uuid();
    cust_eve      UUID := gen_random_uuid();
    cust_frank    UUID := gen_random_uuid();

    -- Orders
    ord_001      UUID := gen_random_uuid();
    ord_002      UUID := gen_random_uuid();
    ord_003      UUID := gen_random_uuid();
    ord_004      UUID := gen_random_uuid();

    -- Transactions
    txn_001      UUID := gen_random_uuid();
    txn_002      UUID := gen_random_uuid();
    txn_003      UUID := gen_random_uuid();
    txn_004      UUID := gen_random_uuid();
    txn_005      UUID := gen_random_uuid();

    -- Refunds
    ref_001      UUID := gen_random_uuid();

    -- Settlements
    set_001      UUID := gen_random_uuid();

    -- Invoices
    inv_001      UUID := gen_random_uuid();

    -- Order Items
    item_001     UUID := gen_random_uuid();
    item_002     UUID := gen_random_uuid();
    item_003     UUID := gen_random_uuid();
    item_004     UUID := gen_random_uuid();
    item_005     UUID := gen_random_uuid();

    -- Journal Entries (should be auto-generated, but add sample for demo)
    je_001       UUID := gen_random_uuid();

    -- Dates
    now_ts       TIMESTAMPTZ := NOW();
    d_7d_ago     TIMESTAMPTZ := NOW() - INTERVAL '7 days';
    d_14d_ago    TIMESTAMPTZ := NOW() - INTERVAL '14 days';
    d_30d_ago    TIMESTAMPTZ := NOW() - INTERVAL '30 days';
BEGIN

-- ============================================================
-- BUYERS（買手）
-- ============================================================

INSERT INTO buyers (id, telegram_user_id, display_name, phone, status,
                    id_type, id_number_encrypted, bank_name, bank_account, bank_account_holder,
                    rating_avg, rating_count, notes)
VALUES
    (buyer_alice, 111111111, 'Alice Wong',     '+852-9111-1111', 'active',
     'hkid', 'ENCRYPTED_A1234567', 'HSBC HK',    'ENCRYPTED_HSBC_111', 'Alice Wong',
     4.80, 42, '資深買手，擅長日本藥妝'),
    (buyer_bob,   222222222, 'Bob Chan',       '+852-9222-2222', 'active',
     'hkid', 'ENCRYPTED_B2345678', 'Hang Seng', 'ENCRYPTED_HSC_222', 'Bob Chan',
     4.55, 28, '新晉買手，主攻韓國美妝'),
    (buyer_carol, 333333333, 'Carol Cheung',   '+852-9333-3333', 'active',
     'passport', 'ENCRYPTED_P9999999', 'Bank of China', 'ENCRYPTED_BOC_333', 'Carol Cheung',
     4.90, 15, '專業買手，歐洲名牌代購')
ON CONFLICT (telegram_user_id) DO NOTHING;

-- ============================================================
-- CUSTOMERS（客戶）
-- ============================================================

INSERT INTO customers (id, telegram_user_id, display_name, phone, email, status, notes)
VALUES
    (cust_david, 444444444, 'David Lee',     '+852-9444-4444', 'david.lee@example.com',    'active', '高價值客戶'),
    (cust_eve,   555555555, 'Eve Ng',       '+852-9555-5555', 'eve.ng@example.com',      'active', '活躍客戶'),
    (cust_frank,  666666666, 'Frank Cheung', '+852-9666-6666', 'frank.cheung@example.com', 'active', '一般客戶')
ON CONFLICT (telegram_user_id) DO NOTHING;

-- ============================================================
-- ORDERS（訂單）
-- ============================================================

-- Order 001: 已完成
INSERT INTO orders (id, order_number, customer_id, status, assigned_buyer_id, assigned_at,
                    total_amount_cents, deposit_paid_cents, balance_due_cents,
                    delivery_address, source_channel, notes)
VALUES
    (ord_001, 'ORD-2026-000001', cust_david, 'completed', buyer_alice, d_14d_ago,
     45000, 20000, 25000,
     '九龍旺角亞皆老街8號朗豪坊', 'telegram',
     '日本藥妝店訂單，包含SK-II精華');

-- Order 002: 配送中
INSERT INTO orders (id, order_number, customer_id, status, assigned_buyer_id, assigned_at,
                    total_amount_cents, deposit_paid_cents, balance_due_cents,
                    delivery_address, source_channel, notes)
VALUES
    (ord_002, 'ORD-2026-000002', cust_eve, 'delivered', buyer_bob, d_7d_ago,
     68000, 30000, 38000,
     '香港島中環荷李活道32號', 'telegram',
     '韓國美妝套裝，包含雪花秀及後');

-- Order 003: 採購中
INSERT INTO orders (id, order_number, customer_id, status, assigned_buyer_id, assigned_at,
                    total_amount_cents, deposit_paid_cents, balance_due_cents,
                    delivery_address, source_channel, notes)
VALUES
    (ord_003, 'ORD-2026-000003', cust_frank, 'in_procurement', buyer_carol, d_30d_ago,
     120000, 60000, 60000,
     '新界沙田廣場3樓', 'telegram',
     '歐洲名牌包包，包括LV Neverfull');

-- Order 004: 待分配
INSERT INTO orders (id, order_number, customer_id, status,
                    total_amount_cents, deposit_paid_cents, balance_due_cents,
                    delivery_address, source_channel, notes)
VALUES
    (ord_004, 'ORD-2026-000004', cust_david, 'pending',
     35000, 0, 35000,
     '九龍九龍城啟德晴朗商場', 'web',
     '待買手接單');

-- ============================================================
-- ORDER ITEMS（訂單明細）
-- ============================================================

INSERT INTO order_items (id, order_id, product_name, product_url, quantity, unit_price_cents, status, notes)
VALUES
    (item_001, ord_001, 'SK-II 神仙水 230ml', 'https://example.com/sk2', 1, 28000, 'procured', '已到貨'),
    (item_002, ord_001, 'Shiseido 打斑精華', 'https://example.com/shiseido', 1, 17000, 'procured', '已到貨'),
    (item_003, ord_002, '雪花秀滋陰套裝', 'https://example.com/sulwhasoo', 2, 22000, 'procured', '已到貨'),
    (item_004, ord_002, '後 天氣丹套裝', 'https://example.com/whooh', 1, 24000, 'pending', '還在採購中'),
    (item_005, ord_003, 'LV Neverfull MM', 'https://example.com/lv', 1, 90000, 'procured', '已購入')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TRANSACTIONS（收款記錄）
-- ============================================================

INSERT INTO transactions (id, transaction_number, order_id, customer_id, type,
                          amount_cents, currency, payment_method, payment_reference,
                          paid_at, status, tg_message_id, notes)
VALUES
    -- Deposit for Order 001
    (txn_001, 'TXN-2026-000001', ord_001, cust_david, 'deposit',
     20000, 'HKD', 'fps', 'FPS-REF-001', d_14d_ago, 'confirmed', NULL,
     'Order ORD-2026-000001 定金'),
    -- Balance for Order 001
    (txn_002, 'TXN-2026-000002', ord_001, cust_david, 'balance',
     25000, 'HKD', 'bank_transfer', 'BT-REF-002', d_7d_ago, 'confirmed', NULL,
     'Order ORD-2026-000001 尾款'),
    -- Deposit for Order 002
    (txn_003, 'TXN-2026-000003', ord_002, cust_eve, 'deposit',
     30000, 'HKD', 'fps', 'FPS-REF-003', d_7d_ago, 'confirmed', NULL,
     'Order ORD-2026-000002 定金'),
    -- Deposit for Order 003
    (txn_004, 'TXN-2026-000004', ord_003, cust_frank, 'deposit',
     60000, 'HKD', 'bank_transfer', 'BT-REF-004', d_30d_ago, 'confirmed', NULL,
     'Order ORD-2026-000003 定金'),
    -- Commission from buyer
    (txn_005, 'TXN-2026-000005', ord_001, buyer_alice, 'commission',
     2250, 'HKD', 'bank_transfer', 'COMM-001', d_7d_ago, 'confirmed', NULL,
     'Buyer Alice 佣金（5% of 45000）')
ON CONFLICT (transaction_number) DO NOTHING;

-- ============================================================
-- REFUNDS（退款記錄）
-- ============================================================

INSERT INTO refunds (id, refund_number, transaction_id, order_id, customer_id,
                     amount_cents, reason, reason_detail, status,
                     approved_by, approved_at, processed_at, notes)
VALUES
    (ref_001, 'REF-2026-000001', txn_003, ord_002, cust_eve,
     30000, 'delay', '客戶等待時間過長，放棄訂單',
     'completed', buyer_bob, d_7d_ago, d_7d_ago, '已全數退還定金')
ON CONFLICT (refund_number) DO NOTHING;

-- ============================================================
-- SETTLEMENTS（買手結算）
-- ============================================================

INSERT INTO settlements (id, settlement_number, buyer_id, period_start, period_end,
                          total_orders, total_sales_cents, commission_rate, commission_amount_cents,
                          status, approved_by, approved_at, paid_at, payment_reference, notes)
VALUES
    (set_001, 'SET-2026-04', buyer_alice,
     '2026-04-01', '2026-04-30',
     12, 580000, 0.0500, 29000,
     'paid', NULL, '2026-05-10', '2026-05-12', 'HSBC-APR-SETTLE',
     '2026年4月結算，已付款至HSBC')
ON CONFLICT (settlement_number) DO NOTHING;

-- ============================================================
-- INVOICES（發票）
-- ============================================================

INSERT INTO invoices (id, invoice_number, customer_id, order_id,
                      amount_cents, status, issued_at, due_date, paid_at, notes)
VALUES
    (inv_001, 'INV-2026-000001', cust_david, ord_001,
     45000, 'paid', d_7d_ago, d_7d_ago + INTERVAL '30 days', d_7d_ago,
     'Order ORD-2026-000001 正式發票')
ON CONFLICT (invoice_number) DO NOTHING;

-- ============================================================
-- DOCUMENTS（文件記錄）
-- ============================================================

INSERT INTO documents (ref_type, ref_id, storage_path, file_name, mime_type, description)
VALUES
    ('buyer', buyer_alice, 'kyc/alice-id-front.jpg', 'alice-hkid-front.jpg', 'image/jpeg',
     'Alice Wong 身份證正面'),
    ('buyer', buyer_alice, 'kyc/alice-id-back.jpg', 'alice-hkid-back.jpg', 'image/jpeg',
     'Alice Wong 身份證背面'),
    ('buyer', buyer_bob, 'kyc/bob-passport.jpg', 'bob-passport.jpg', 'image/jpeg',
     'Bob Chan 護照'),
    ('order', ord_001, 'receipts/2026/05/ord001-receipt.jpg', 'ord001-receipt.jpg', 'image/jpeg',
     'Order ORD-2026-000001 收據'),
    ('order', ord_002, 'receipts/2026/05/ord002-receipt.jpg', 'ord002-receipt.jpg', 'image/jpeg',
     'Order ORD-2026-000002 收據')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BUYER DOCUMENTS（買手KYC文件）
-- ============================================================

-- (if buyer_documents table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'buyer_documents'
    ) THEN
        INSERT INTO buyer_documents (buyer_id, document_type, storage_path, status, notes)
        VALUES
            (buyer_alice, 'hkid_front', 'kyc/alice-id-front.jpg', 'verified', '已核實'),
            (buyer_alice, 'hkid_back',  'kyc/alice-id-back.jpg',  'verified', '已核實'),
            (buyer_alice, 'bank_proof', 'kyc/alice-bank.pdf',     'pending', '等待銀行月結單'),
            (buyer_bob,   'passport',  'kyc/bob-passport.jpg',  'verified', '已核實')
        ON CONFLICT DO NOTHING;
    END IF;
END;
$$;

-- ============================================================
-- JOURNAL ENTRIES（會計分錄 — 示範）
-- ============================================================
-- 注意：生產環境應該由 trigger 自動產生，這裡只是 Seed 示範

DO $$
DECLARE
    acc_cash UUID;
    acc_rev  UUID;
BEGIN
    SELECT id INTO acc_cash FROM accounts WHERE account_code = '1101';
    SELECT id INTO acc_rev  FROM accounts WHERE account_code = '4101';

    IF acc_cash IS NULL OR acc_rev IS NULL THEN
        RAISE NOTICE 'Accounts not seeded yet — skipping journal entries seed';
    ELSE
        -- Example: Customer payment
        INSERT INTO journal_entries (
            entry_number, entry_date, source_type, source_id, source_ref,
            memo, posted_by, posted_by_role
        ) VALUES (
            'JE-2026-05-0001',
            CURRENT_DATE - INTERVAL '7 days',
            'transaction',
            txn_001,
            'TXN-2026-000001',
            'Seed: Deposit received: TXN-2026-000001',
            'system', 'system'
        );

        INSERT INTO journal_lines (entry_id, account_id, debit_cents, credit_cents, memo)
        SELECT currval('journal_entries_id_seq'), acc_cash, 20000, 0,
               'DR: Deposit received: TXN-2026-000001';

        INSERT INTO journal_lines (entry_id, account_id, debit_cents, credit_cents, memo)
        SELECT currval('journal_entries_id_seq'), acc_rev, 0, 20000,
               'CR: Procurement service revenue: TXN-2026-000001';
    END IF;
END;
$$;

-- ============================================================
-- 完成
-- ============================================================

RAISE NOTICE '✅ BuyerOS seed data inserted successfully';
RAISE NOTICE '   Buyers: 3';
RAISE NOTICE '   Customers: 3';
RAISE NOTICE '   Orders: 4';
RAISE NOTICE '   Transactions: 5';
RAISE NOTICE '   Refunds: 1';
RAISE NOTICE '   Settlements: 1';
RAISE NOTICE '   Invoices: 1';

END;
$$;

COMMIT;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check counts
SELECT 'buyers' AS table_name, COUNT(*) AS row_count FROM buyers
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'refunds', COUNT(*) FROM refunds
UNION ALL
SELECT 'settlements', COUNT(*) FROM settlements
UNION ALL
SELECT 'invoices', COUNT(*) FROM invoices
ORDER BY table_name;
