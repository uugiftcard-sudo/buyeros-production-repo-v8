# BuyerOS 第三方服務設定指南

本指南說明如何將 Stripe、PayPal、Google Sheets、Shopify 等第三方服務接入 BuyerOS。

## 目錄

1. [支付退款](#1-支付退款)
2. [財務數據](#2-財務數據-google-sheets)
3. [電商訂單與買家](#3-電商訂單與買家-shopify)
4. [環境變量速查](#4-環境變量速查)

---

## 1. 支付退款

責任邊界：退款對帳、退款比對、OCR 入帳和 manual review 屬於
`buyer_ai` 買手線。Shopify、Stripe、PayPal 或自定義網店 API 在這裡只提供
支付/訂單/售後資料來源；`commerce` 不主責退款對帳。

### Stripe

1. 在 [Stripe Dashboard](https://dashboard.stripe.com/apikeys) 取得 `sk_live_...` 或 `sk_test_...` key
2. 在 `.env` 中設定：
   ```
   STRIPE_API_KEY=sk_test_...
   STRIPE_API_VERSION=2024-04-10
   ```
3. Stripe 會自動處理退款，並在 Dashboard 中留下記錄

### PayPal

1. 在 [PayPal Developer Dashboard](https://developer.paypal.com/) 建立 App，取得 Client ID 和 Secret
2. 確認 `PAYPAL_MODE`（`sandbox` 或 `live`）
3. 在 `.env` 中設定：
   ```
   PAYPAL_CLIENT_ID=...
   PAYPAL_CLIENT_SECRET=...
   PAYPAL_MODE=sandbox
   ```

### 自定義 REST API

如果使用自己的退款 API：
```
PAYMENT_GATEWAY_BASE_URL=https://your-refund-api.com
PAYMENT_GATEWAY_API_KEY=your-api-key
```

API 預期 contract：
- `POST {PAYMENT_GATEWAY_BASE_URL}/refunds`
- Body: `{"transaction_id": "...", "amount": optional, "reason": optional}`
- Auth: `Authorization: Bearer {PAYMENT_GATEWAY_API_KEY}`

---

## 2. 財務數據（Google Sheets）

### 前提條件

- 一個 Google Cloud 專案
- 啟用 **Google Sheets API**
- 一個共用的 Google Sheets 文件

### 方式 A：Service Account（推薦，用於 Server-side）

1. 在 Google Cloud Console 建立 Service Account
2. 建立 JSON Key，下載並填入 `.env`：
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...@....iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token"}'
   ```
3. 在 Google Sheets 中，點擊「共用」→ 輸入 Service Account 的 email（`....iam.gserviceaccount.com`）→ 給予「編輯者」權限

### 方式 B：API Key（僅讀取公開 Sheets）

1. 在 Google Cloud Console 建立 API Key
2. 在 `.env` 中設定：
   ```
   GOOGLE_SHEETS_API_KEY=AIza...
   ```
3. 確保 Sheets 文件已設為「知道連結的任何人都可檢視」

### 工作表格式約定

BuyerOS 預期以下工作表存在於 Spreadsheet 中：

**工作表 1：利潤**
| A | B | C |
|---|---|---|
| 月份 | HKD金額 | 退款筆數 |
| 2026-01 | 48500 | 3 |

**工作表 2：出糧日程**
| A | B | C |
|---|---|---|
| 下次出糧日 | 幣種 | 狀態 |
| 5 | HKD | pending |

設定 `GOOGLE_SHEETS_ID` 為文件 URL 中的 ID：
```
https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/edit
```

---

## 3. 電商訂單與買家（Shopify）

### 建立 Shopify Custom App

1. 在 Shopify Admin → **Settings** → **Apps and sales channels** → **Develop apps**
2. 點擊 **Create an app**，命名為「BuyerOS」
3. 在 **API credentials** 標籤，點擊 **Install app** 並複製 **Admin API access token**
4. 設定 API 範圍：
   - `read_orders` — 讀取訂單
   - `read_customers` — 讀取買家資料

### 在 `.env` 中設定

```
SHOPIFY_SHOP_DOMAIN=yourstore.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
```

### 自定義電商 REST API

如果使用自己的訂單/買家 API：

```
# 訂單
ORDERS_API_BASE_URL=https://api.yourshop.com
ORDERS_API_KEY=your-api-key

# 買家
BUYERS_API_BASE_URL=https://api.yourshop.com
BUYERS_API_KEY=your-api-key
```

**訂單 API 預期 contract：**
- `GET {ORDERS_API_BASE_URL}/orders/{order_id}` → 訂單詳情 JSON
- `GET {ORDERS_API_BASE_URL}/orders?user_id={user_id}` → 訂單列表

**買家 API 預期 contract：**
- `GET {BUYERS_API_BASE_URL}/customers/{buyer_id}` → 買家資料 JSON
- `GET {BUYERS_API_BASE_URL}/customers` → 買家列表

---

## 4. 環境變量速查

將以下變量加入 `.env`：

```bash
# === 支付退款 ===
STRIPE_API_KEY=sk_test_...
STRIPE_API_VERSION=2024-04-10
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=sandbox
PAYMENT_GATEWAY_BASE_URL=https://your-api.com
PAYMENT_GATEWAY_API_KEY=...

# === 財務 ===
GOOGLE_SHEETS_ID=1a2b3c4d5e6f...
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
# 或
GOOGLE_SHEETS_API_KEY=AIza...

# === 電商 ===
SHOPIFY_SHOP_DOMAIN=yourstore.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...
ORDERS_API_BASE_URL=https://api.yourshop.com
ORDERS_API_KEY=...
BUYERS_API_BASE_URL=https://api.yourshop.com
BUYERS_API_KEY=...
```

---

## 驗證設定

部署後，訪問 `/system/capabilities` 端點查看各服務的連線狀態：

```bash
curl -H "Authorization: Bearer $BUYEROS_API_KEY" \
  https://your-domain.com/system/capabilities
```

在返回的 `feature_flags` 中確認各項為 `true`。
