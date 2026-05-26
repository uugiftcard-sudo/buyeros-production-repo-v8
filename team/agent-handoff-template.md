---
name: agent-handoff-template
description: 新 agent 開工 template — 每次開新 chat 用呢個，確保佢讀到 shared state，唔靠口述
type: reference
---

# Agent Handoff Template

每次開新 chat / 新 session，找另一個 agent 幫手，開場白複製以下：

---

```
📋 Handoff — CLOTH P1-D
請先讀共享狀態：
- /Users/rubykan/Documents/team/state.md
- /Users/rubykan/Documents/team/projects/cloth.md
- /Users/rubykan/Documents/team/agents.md
Repo：
- /Users/rubykan/Documents/CLOTH
開始前：
- 先跑 git status
- 不要覆蓋其他 agent 已改嘅文件
- 不要重做 P1-A/B/C
已完成：
- P1-A Mobile navigation ✅
- P1-B product market persistence ✅
- P1-C input validation + structured error handling ✅
P1-D 目標：
- 做 API smoke contracts，唔大型重構
- 補 products / orders / finance / inventory / support smoke contract
- 驗證 create / update / delete / market filter / required validation
- 如果發現 filtering / pagination 缺口，記低並拆去 Phase 2，唔好順手大改
關鍵檔案：
- api/src/routes/products.ts
- api/src/routes/orders.ts
- api/src/routes/finance.ts
- api/src/routes/inventory.ts
- api/src/routes/support.ts
- api/src/models/store.ts
- scripts/api-validation-errors.test.mjs
- scripts/product-market-persistence.test.mjs
- scripts/mobile-nav-contract.test.mjs
驗收：
cd /Users/rubykan/Documents/CLOTH
node --test scripts/api-validation-errors.test.mjs
node --test scripts/product-market-persistence.test.mjs
node --test scripts/mobile-nav-contract.test.mjs
node --import tsx --test api/src/db/sqlite-store.test.ts
npm run lint
npm run check
回覆用廣東話，完成後更新 /Users/rubykan/Documents/team/state.md 同 /Users/rubykan/Documents/team/projects/cloth.md
```

---

## 為什麼咁重要

- **每個新 session 開頭都先讀 `state.md` / `cloth.md`，唔好靠上一個 chat 嘅口述**
- 所有 agent 獨立 session，唔靠 chat history
- 靠 `state.md` + `cloth.md` 接力
- 每次新 session 第一句就係叫佢讀 shared files

## 常見問題

Q: 另一個 agent 幾時知道自己做咗？
A: 佢做完後要自己 update `state.md` + `cloth.md`，你帮佢检查有冇 commit

Q: 如果佢唔記得讀 state.md？
A: 呢個 template 係强制要求，唔讀就做嘢係預期之外嘅行為

Q: 可以直接喺同一個 chat 做完所有嘢嗎？
A: 可以，但如果你想分工，就用呢個 template 開新 chat 俾另一個 agent
