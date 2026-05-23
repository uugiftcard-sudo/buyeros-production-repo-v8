# P3: RLS 確認 + Audit Log 文檔

> 對應：`supabase/migrations/0003_rls_and_audit.sql`
> 日期：2026-05-23

---

## 1. 做了什麼

### 1.1 RLS Audit Function

`recon_rls_audit()` — 一次性 SQL function，運行後返回所有 table 的 RLS 狀態：

| 狀態 | 顏色 | 意義 |
|------|------|------|
| 🟢 RLS ON WITH POLICIES | 安全 | 有 RLS + 有 policies |
| 🟡 RLS ON, NO SELECT POLICY | 需修復 | 有 RLS 但 SELECT 冇 policy |
| 🔴 RLS ON, NO POLICY | 危險 | RLS on 但冇 policy = deny all |
| 🔴 NO RLS — ALL ROWS PUBLIC | **極危險** | 任何人可看所有數據 |

**使用方式**：在 Supabase Studio SQL Editor 執行：
```sql
SELECT * FROM recon_rls_audit();
```

### 1.2 RLS Policy 模板

提供了三套 Policy Template，根據你的 Auth 方式選擇：

**Option A：Supabase Auth（推薦）**
- 每個 table 加 `auth_user_id UUID REFERENCES auth.users(id)` column
- Policy: `auth.uid() = auth_user_id`
- Admin 用 service_role key bypass RLS

**Option B：Telegram OAuth**
- JWT claims 包含 `telegram_user_id`
- Policy: JWT 方式檢查

**Option C：Server-Side Only（Bot 是唯一 client）**
- RLS 全部 DENY
- 所有 access 經 Edge Functions 用 service_role key

### 1.3 Audit Log

**設計原則**：Append-only，不可篡改

```
┌─────────────────────────────────────────────┐
│  Table 變更 → audit_log INSERT (always OK)  │
│              ↕ NO UPDATE                    │
│              ↕ NO DELETE                    │
└─────────────────────────────────────────────┘
```

### 1.4 覆蓋的 Tables

| Table | RLS Policy | Audit Trigger |
|-------|-----------|--------------|
| buyers | ✅ Template | ✅ |
| customers | ✅ Template | ✅ |
| orders | ✅ Template | ✅ |
| transactions | ✅ Admin-only | ✅ |
| refunds | ✅ Admin-only | ✅ |
| settlements | ✅ Template | ✅ |
| invoices | ✅ Template | ❌ |
| documents | ✅ Template | ❌ |
| journal_entries | ✅ Admin-only | ✅ |
| journal_lines | ✅ Admin-only | ❌ |
| accounts | ✅ Admin-only | ❌ |
| accounting_periods | ✅ Admin-only | ❌ |

---

## 2. 立即行動（Apply 前）

### 2.1 確認 Auth 方式

在 Supabase Studio → Authentication → Settings 確認：
- 有冇 Supabase Auth users？
- 還是用 Telegram 直接認證？

### 2.2 測試 RLS

```sql
-- 在 Supabase Studio SQL Editor 測試：
SELECT * FROM recon_rls_audit();

-- 任何 🔴 的 table 都要立即處理
```

### 2.3 測試 Audit Log 不可篡改性

```sql
-- 在 Supabase Studio 測試（應該失敗）：
UPDATE audit_log SET reason = 'test' WHERE id = 'any-id';
-- 預期錯誤：audit_log is append-only

DELETE FROM audit_log WHERE id = 'any-id';
-- 預期錯誤：audit_log is append-only
```

---

## 3. Audit Log 查詢

### 查某記錄的完整變更歷史
```sql
SELECT * FROM audit_trail('orders', '<order-uuid>');
```

### 查某用戶的所有操作
```sql
SELECT * FROM audit_by_user('<auth-user-uuid>');
```

### 查最近 7 天的所有變更
```sql
SELECT * FROM audit_log
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 100;
```

---

## 4. 敏感資料遮蔽（GDPR）

`audit_mask_sensitive()` function 自動遮蔽：
- `id_number_encrypted`
- `bank_account`
- `phone`
- `email`

---

## 5. 保留政策

| 數據類型 | 儲存位置 | 保留期 |
|---------|---------|--------|
| 90 天內 audit log | Supabase DB | 90 天 |
| 90 天外 audit log | Cloudflare R2 (JSONL) | 7 年 |
| 財務 journal entries | Supabase DB | 永久 |

---

*P3 完成日期：2026-05-23*
