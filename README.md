# Show Me The Story — AI 小说生成器（白泽改造版）

> 分支自 NousResearch/show-me-the-story
> English: [README.en.md](README.en.md)

一个长篇小说 AI 创作工具。单文件运行，内置 Web 界面，对接任意 OpenAI 兼容 API。

不同于原版，**本分支的改动方向是：剔除冗余、明确层级、代码硬约束。**

---

## 改造清单

### ✅ 已完成

| # | 改造 | 效果 |
|---|------|------|
| 1 | Mem0 内存优化：sentence_transformers→fastembed | 内存 ~800MB→~200MB |
| 2 | 提示词三权分层：🔴核心指令 / 🟡约束 / 🟢参考 | AI 不再混清优先级 |
| 3 | 完整大纲改定位：从「逐章指令」→「背景参考」 | 不提前泄后期剧情 |
| 4 | 摘要 500 字代码截断（非软提示） | 摘要稳定可控 |
| 5 | 删写作 prompt 的 PreviousEnding（保留一致性检查 400 字） | 省 ~400 字/章 token |
| 6 | 声明检索：章节大纲独立 JSON 索引，纯关键词搜索 | 不走向量不 embedding |
| 7 | Skill 注入过滤：craft 类不再自动注入 agent chat | 减少噪音 |
| 8 | get_narrative_position 工具：故事弧位置感知 | 辅助内容规划 |
| 9 | 后端修复：竞态修复 / ensureProject / 编辑限制放开 | 运行更稳定 |

### ⬜ 未完成

- craft 修订按钮（改动一·阶段二，等声明检索积累数据后做）

---

## 怎么用

```bash
./show-me-the-story /path/to/storys
```

浏览器打开 `http://localhost:48090` → 创建项目 → 填设定 → AI 生成大纲 → 确认后逐章写作。

首次用需在「API 配置」填接口地址和密钥（支持 DeepSeek / OpenAI / Ollama / LM Studio 等）。

---

- **拐子** — 方案、决策、需求
- **白泽** — 实现

> 原始项目：NousResearch/show-me-the-story · Apache 2.0
