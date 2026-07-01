# Show Me The Story — AI 小说生成器 (白泽改造版)

> 原版作者：nigh · MIT

以下是一个原版与本版的差异对表。

| # | 原版 | 本版 |
|---|------|------|
| 1 | StorySynopsis 作为逐章写作指令注入 | 改为「完整大纲（背景参考）」，仅提供方向性信息，写作以本章大纲为准，前端标签同步 |
| 2 | prompt 全部平铺，无优先级区分 | 分三层注入：🔴核心指令 > 🟡约束 > 🟢参考 |
| 3 | WritingStyle 独立字段注入 | 删除（已由写作人格 persona 覆盖） |
| 4 | 每章写作注入上一章尾部 800 字原文（PreviousEnding） | 删除（一致性检查保留，400 字限制） |
| 5 | 摘要字数靠 AI 自觉 | 代码层 500 字硬截断 |
| 6 | 无章节大纲检索功能 | `.declarations/declarations.json` 纯关键词索引，写作页 🔍 搜索按钮 + Agent 工具，不自动注入 |
| 7 | Mem0 用 sentence_transformers | 替换为 fastembed+onnxruntime，内存 ~800MB→~200MB |
| 8 | craft 类 skill 自动注入 Agent chat | 过滤，仅 polish 类自动注入 |
| 9 | 无故事弧位置感知 | get_narrative_position agent 工具 + 系统 prompt 注入当前阶段信息 |

拐子（方案/决策）· 白泽（实现）
