# One4all Gift Card Balance Tracker (Mac Messages -> Google Sheets)

這個小工具會從 macOS 的 Messages 資料庫 `~/Library/Messages/chat.db` 讀取 One4all 回覆訊息，解析出：

- 卡號末 4 位（ending with XXXX）
- 餘額（GBP）
- 查詢日期、時間戳

然後把結果追加寫入 Google Sheets。

## 1) 先完成 iPhone/Mac SMS 轉寄

iPhone → 設定 → 訊息 → 文字訊息轉寄 → 開啟你的 Mac。

（否則 Mac 只會收到 iMessage，收不到 SMS short code 回覆。）

## 2) 建立 Google Sheets API 憑證

### A. Google Cloud Console

1. 去 https://console.cloud.google.com
2. 建立一個 Project
3. APIs & Services → Library → 啟用 **Google Sheets API**
4. IAM & Admin → Service Accounts → Create service account
5. 建立 key：Keys → Add key → Create new key → JSON
6. 下載後把檔案改名為 `credentials.json` 放到本資料夾

### B. 分享你的 Sheet 給 Service Account

打開 `credentials.json`，找到 `client_email`，例如：

`xxxxx@xxxxx.iam.gserviceaccount.com`

然後在 Google Sheets 右上角 Share，把這個 email 加入（至少 Editor 權限）。

## 3) 設定 config

編輯 `config.py`：

- `SHEET_ID`：Google Sheet 的 URL 裡面那串 ID
  - `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0`
- `WORKSHEET_NAME`：工作表名稱（預設 `balances`）

## 4) 安裝依賴 & 執行

```bash
cd /Users/rubykan/Documents/gift_card_tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 sms_parser.py
```

成功時會輸出：

- `Wrote N rows to worksheet 'balances'.`

## 5) 權限注意（macOS）

這個腳本讀取的是 `chat.db`（Messages 的 SQLite）。

如果你遇到「permission denied」或讀不到資料，請到：

System Settings → Privacy & Security → Full Disk Access

把你執行 python 的終端（Terminal / iTerm）加進去。

## 欄位格式

腳本會寫入 5 欄：

1. Card Last 4
2. Balance GBP
3. Query Date (YYYY-MM-DD)
4. Timestamp (YYYY-MM-DD HH:MM:SS)
5. Message ID
