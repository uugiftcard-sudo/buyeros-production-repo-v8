---
name: agents
description: 團隊成員資料 — 每個成員嘅角色、位置、能力範圍
type: reference
---

# 團隊成員

## Claude（呢個 instance）
- **角色：** AI coding assistant，由 @uu 統籌
- **工作方式：** 喺同一個 chat thread，睇得到所有對話
- **強項：** 讀 code、寫 code、debug、architect、文件
- **位置：** 跟住 conversation走，冇固定 session
- **每次 startup：** 讀 `team/state.md` + `team/projects/[name].md`

## @uu
- **角色：** 统筹/Architect，負責分配工作、決定方向
- **語言：** 粵語 Cantonese
- **其他專案：** CLOTH、BuyerOS 等

---

## 如何加入新成員
喺呢個檔案加 entry，格式：
```markdown
## [Name]
- **角色：** ...
- **工作方式：** ...
- **強項：** ...
- **位置：** ...
```
