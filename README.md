# Show Me The Story — AI 小说生成器 (白泽改造版)

> 基于 [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story) 改造。以下是与原版的差异。

| # | 原版 nigh | 本版 |
|---|-----------|------|
| 1 | **无 Mem0 叙事记忆** | 新增完整 Mem0 侧车（mem0.go + Python FastAPI 服务 + BAAI/bge-small-zh-v1.5 本地模型），后续替换 sentence_transformers→fastembed+onnxruntime，内存 ~800MB→~200MB |
| 2 | **prompt 全部平铺**：StorySynopsis / HistorySummary / PreviousEnding / WritingStyle / WritingPOV / 角色 / 世界观 / Memory 无差别混排 | **三权分层注入**：🔴核心指令（本章大纲·叙述视角·字数）> 🟡约束（前情·项目指导·伏笔）> 🟢参考（完整大纲·角色·世界观·记忆）。删除 WritingStyle（已由 persona 覆盖）。PreviousEnding 移出写作 prompt 仅保留一致性检查 |
| 3 | **StorySynopsis 标签「故事梗概」**，作为逐章写作指令 | 标签改为「完整大纲（背景参考）」，前端同步。原按章节 AI 生成大纲不变，用户可额外上传完整大纲，两者分层共存 |
| 4 | **摘要字数无硬限制** | 代码层 500 字硬截断 |
| 5 | **无章节大纲关键词检索** | 新增 `.declarations/declarations.json` 纯关键词索引，写作页搜索按钮 + Agent 工具 `search_declarations`，按需调用不自动注入 |
| 6 | **无故事弧位置感知** | 新增 `get_narrative_position` agent 工具 + 系统提示注入当前阶段 |
| 7 | **craft 类 skill 与 polish 无差别自动注入** | craft 类过滤，仅 polish 类自动注入 |
| 8 | **后端缺 ensureProject 保护 / doConfirm 竞态 / 大纲编辑限制** | 全部修 |

拐子（方案）· 白泽（实现）
