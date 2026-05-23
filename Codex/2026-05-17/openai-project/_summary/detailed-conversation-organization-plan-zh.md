# AI 對話整理總計劃書

更新日期：2026-05-17

## 1. 計劃目的

呢份計劃書嘅目標，係將你散落喺 ChatGPT、Claude、Gemini、Perplexity、Telegram 同其他平台嘅對話、project、匯出檔、重點決策、可重用 prompt，同埋後續待辦，統一整理成一套長期可維護、可搜尋、可歸檔、可視覺化管理嘅系統。

最終效果唔係單純「儲埋啲檔」，而係做到：

- 一眼睇到你有邊啲 AI project
- 知道每個 project 有冇真實對話記錄落地
- 分得清邊啲係正式匯出、邊啲只係連結、邊啲只係普通壓縮檔
- 重要決策、prompt、待辦可以被二次利用
- 之後每星期只花少量時間都可以持續更新

## 2. 工作範圍

今次整理會分做五類資產：

1. ChatGPT project 連結
2. 官方對話匯出檔
3. 非官方但可能包含對話內容嘅檔案
4. 其他平台嘅聊天或 bot 對話記錄
5. 方便閱讀同搜尋嘅整理層，例如 CSV、Markdown、Notion

## 3. 目前已確認資產

### 3.1 ChatGPT project 連結

已收錄 7 個 ChatGPT project 連結：

- Mai Shou AI So
- UU
- Giftcard AI System
- ZYVA Smart Payment Test
- ZYVA Start Up
- SMS Bot Profile
- OpenClaw Zhu Shou

目前狀態：

- 已入總表
- 仍然未有正式匯出檔
- 由於需要登入帳戶，現階段未能直接讀取 project 內文

### 3.2 已下載檔案檢查結果

截至 2026-05-17，已喺本地整理區內發現以下檔案：

#### A. Telegram 匯出

位置：

- `/Users/rubykan/Documents/Codex/2026-05-17/openai-project/Raw-Exports/Other-AI/Telegram/`

內容狀態：

- 有 15+ 個 HTML 匯出頁面
- 屬於 Telegram `ChatExport_2026-04-02`
- 抽樣內容以人與人對話為主
- 內文有零星提及 `chatgpt`
- 亦見到 bot 連結同 bot 按鈕痕跡

判斷：

- 呢批檔案屬於「已下載對話記錄」
- 但唔屬於官方 ChatGPT / Claude 對話匯出
- 有機會包含你喺 Telegram 入面討論 AI、分享 prompt、分享 AI 連結嘅內容
- 值得保留並做二次掃描

#### B. `free-claude-code-main.zip`

位置：

- `/Users/rubykan/Documents/Codex/2026-05-17/openai-project/Raw-Exports/Claude/free-claude-code-main.zip`

內容狀態：

- 已檢查壓縮檔清單
- 內含 `README.md`、`PLAN.md`、`api/`、`cli/`、`config/` 等程式專案檔
- 結構明顯係一個 code project archive

判斷：

- 呢個檔案唔係 Claude 對話匯出
- 應該視為 Claude 相關專案壓縮包，而唔係聊天記錄
- 要保留，但唔應混入正式對話資料庫核心內容

#### C. ChatGPT / Claude / Gemini / Perplexity 官方匯出檔

截至 2026-05-17：

- `ChatGPT`：未發現正式匯出檔
- `Claude`：未發現正式對話匯出檔
- `Gemini`：未發現正式對話匯出檔
- `Perplexity`：未發現正式對話匯出檔

結論：

- 目前真正已落地嘅「對話記錄」只有 Telegram HTML 匯出
- 目前真正已落地嘅「AI 平台官方對話匯出」仍然係 0

## 4. 整理原則

為免之後越整理越亂，以下原則固定採用：

### 4.1 原始檔永遠保留

- 所有匯出原檔一律留喺 `Raw-Exports/`
- 不在原檔上直接改名、覆寫、裁切內容
- 所有處理後版本放入 `Processed/`

### 4.2 連結、原檔、摘要分層管理

- 連結：放 `master-index.csv`
- 原檔：放 `Raw-Exports/`
- 摘要：放 `_summary/*.md`
- 視覺化管理：日後放 Notion

### 4.3 對話資產分三級

`Level 1`

- 官方匯出
- 可信度最高
- 優先整理

`Level 2`

- 平台內 project 連結
- 有內容價值，但未正式匯出

`Level 3`

- Telegram、截圖、轉貼、普通 zip、分享頁
- 只作輔助線索或補充材料

## 5. 最終整理目標

最終希望建立 3 層架構：

### 5.1 本地整理層

作用：

- 保存原始證據
- 避免平台內容遺失
- 可備份

主要檔案：

- `Raw-Exports/`
- `Processed/`
- `_summary/master-index.csv`
- `_summary/master-summary.md`
- `_summary/projects-overview.md`

### 5.2 索引層

作用：

- 將所有對話變成可篩選嘅結構化資料
- 為 Notion 匯入做準備

主要欄位：

- Title
- Platform
- Project
- Date
- Status
- Priority
- Tags
- Summary
- Key Decisions
- Next Actions
- Source Link
- Raw File
- Reusable Prompt
- Notes

### 5.3 閱讀層

作用：

- 平時快速睇返內容
- 用於重點追蹤同工作管理

建議工具：

- Notion

## 6. 執行階段

### Phase 1：收集

目標：

- 將所有可找到嘅原始資料集中入同一個 workspace

現狀：

- 已完成基本資料夾結構
- 已收錄 ChatGPT project links
- 已搬運 Telegram 匯出
- 已搬運一個 Claude 相關 zip

未完成：

- 官方 ChatGPT 匯出
- 官方 Claude 匯出
- Gemini 對話導出
- Perplexity 對話導出

### Phase 2：辨識

目標：

- 判斷每份檔案屬於正式對話、普通材料、專案檔、還是噪音

目前辨識結果：

- Telegram HTML：正式聊天記錄，但非 AI 平台官方匯出
- `free-claude-code-main.zip`：程式專案壓縮包，非對話記錄
- ChatGPT project links：有效線索，但未落地成對話匯出

### Phase 3：清洗

要做嘅事：

- 去重 project links
- 為每條記錄補上正確 `Platform`、`Project`、`Status`
- 標記 `official-export`、`link-only`、`non-chat-archive`、`telegram-review`

### Phase 4：摘要

要做嘅事：

- 每條有價值對話寫 2 至 5 句摘要
- 抽出決策
- 抽出可重用 prompt
- 抽出下一步行動

### Phase 5：Notion 落地

要做嘅事：

- 建立 `AI Conversations` database
- 匯入 `master-index.csv`
- 設立 views
- 整理首頁 dashboard

### Phase 6：長期維護

要做嘅事：

- 每星期一次整理
- 每次新增對話只做增量更新
- 每月做一次 archive

## 7. Notion 最終結構

### 主頁

建議名稱：

- `AI Conversations Hub`

主頁區塊：

- Overview
- Inbox
- Active Projects
- Important Conversations
- Prompt Library
- Decisions
- Archive

### Database

建議名稱：

- `AI Conversations`

建議 views：

- All Conversations
- Inbox
- By Project
- Important
- By Platform
- Prompt Library
- Follow-Up Needed

## 8. 命名規則

為免日後越加越亂，建議固定格式：

### 檔案

`YYYY-MM-DD_platform_project_description`

例子：

- `2026-05-17_chatgpt_uu_export.zip`
- `2026-05-17_telegram_ai-notes_messages.html`

### 對話標題

`Project Name - Topic`

例子：

- `UU - Payment Flow Brainstorm`
- `Giftcard AI System - Prompt Revision`

## 9. 風險與處理方式

### 風險 1：平台未匯出即遺失

處理：

- 盡快做官方匯出
- 將所有重要 project 優先落地

### 風險 2：普通 zip 被誤當對話

處理：

- 所有壓縮檔先列目錄再判定
- 未驗證前標記為 `unverified`

### 風險 3：Telegram 雜訊太多

處理：

- 只抽 AI 關鍵字
- 只抽 prompt、link、決策、bot 對話

### 風險 4：Notion 入得太亂

處理：

- 先整理本地 master-index
- 後匯入 Notion
- 唔直接將雜亂 raw material 全塞入主 database

## 10. 即時下一步

以下係最值得即刻做嘅順序：

1. 匯出 ChatGPT 官方資料
2. 匯出 Claude 官方資料
3. 將新檔放入 `Downloads`
4. 跑 `import_exports.sh`
5. 更新 `master-index.csv`
6. 將已確認正式對話匯入 Notion
7. 對 Telegram 匯出做 AI 關鍵字掃描

## 11. 驗收標準

當以下條件達成，就代表呢套整理系統算完成第一階段：

- 所有 AI 平台至少各有一個明確分類位置
- 所有已知 project links 都已入表
- 所有本地已下載檔案都已判斷類型
- `master-index.csv` 可以作為唯一總索引
- Notion 有一個可閱讀 dashboard
- 可以快速回答「某個 project 有冇對話匯出」同「某條資料喺邊」

## 12. 目前總結

截至 2026-05-17，目前狀態可以簡單總結為：

- 你嘅整理系統骨架已經建立
- ChatGPT project links 已經集中記錄
- Telegram 對話記錄已經成功收納
- `free-claude-code-main.zip` 已確認係 code archive，唔係對話匯出
- 真正缺口係：ChatGPT、Claude、Gemini、Perplexity 官方對話匯出仍未落地

所以，現階段最重要唔係再加新欄位，而係盡快將官方匯出檔落地，之後我就可以幫你做真正嘅內容級整理。
