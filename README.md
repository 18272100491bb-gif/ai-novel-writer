# Show Me The Story — AI 小说生成器 (白泽改造版)

> 原版作者：nigh · MIT

以下是与原版的差异对表。

| # | 原版 | 本版 |
|---|------|------|
| 1 | StorySynopsis 作为逐章指令注入 | 改为「完整大纲（背景参考）」，原按章节生成大纲模块保留，新增用户自行上传完整大纲，两者分层共存 |
| 2 | prompt 全部平铺无优先级 | 分三层注入：🔴核心指令 > 🟡约束 > 🟢参考 |
| 3 | WritingStyle 独立注入 | 删除（已由写作人格 persona 覆盖） |
| 4 | 每章写作注入上一章尾部 800 字原文 | 写作 prompt 删除，一致性检查保留（400 字限制） |
| 5 | 摘要字数靠 AI 自觉 | 代码层 500 字硬截断 |
| 6 | 无章节大纲检索 | `.declarations/declarations.json` 纯关键词索引，写作页搜索按钮 + Agent 工具，按需调用不自动注入 |
| 7 | Mem0 用 sentence_transformers | 替换 fastembed+onnxruntime (BAAI/bge-small-zh-v1.5，本地不走外部 API)，内存 ~800MB→~200MB，侧车独立部署，前端视图加大重试保护 |
| 8 | craft 类 skill 自动注入 Agent chat | 过滤，仅 polish 类自动注入 |
| 9 | 无故事弧位置感知 | get_narrative_position agent 工具 + 系统提示注入 |
| 10 | 后端缺 ensureProject 保护 / doConfirm 竞态 / 大纲编辑限制 | 全部修 |

拐子（方案/决策）· 白泽（实现）
