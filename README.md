# Show Me The Story — AI 小说生成器（白泽改造版）

> Forked from [NousResearch/show-me-the-story](https://github.com/NousResearch/show-me-the-story)
>
> English: [README.en.md](README.en.md)

一个开箱即用的长篇小说 AI 创作工具。单个可执行文件，内置完整 Web 界面，连接任意 OpenAI 兼容 API（DeepSeek、OpenAI、Ollama、LM Studio 等）即可自动生成大纲并逐章创作长篇小说。

---

## 改造内容（vs 原始 SMTS）

### 一、架构级改造

#### 1. Mem0 叙事记忆引擎优化
- **替换 embedding 库**：`sentence_transformers` → `fastembed`（TextEmbedding）+ `onnxruntime`
- **结果**：内存占用从 ~800MB 降至 ~200MB，无需外部依赖
- **本地模型**：`BAAI/bge-small-zh-v1.5`，不走外部 API
- **Mem0 侧车独立部署**：Python FastAPI 侧车进程（端口 49152），与 Go 后端解耦

#### 2. 提示词架构 — 三权分层
- user prompt 从「全部平铺混合」改为三层权值：
  - **🔴 核心指令**（本章大纲 · 叙述视角 · 字数控制）— 必须严格遵守
  - **🟡 约束**（前情提要 · 伏笔状态 · 项目创作指导）— 不可违背
  - **🟢 参考**（完整大纲背景 · 角色 · 世界观 · 叙事记忆）— 方向性背景
- 系统 prompt（persona）与 user prompt 职责彻底分离
- 删除 `WritingStyle`（已被 persona 覆盖），删除 `PreviousEnding` 从写作 prompt

#### 3. 完整大纲 → 背景参考
- 原始 SMTS 将 StorySynopsis 当成逐章指令
- 改造后完整大纲定位为「定调子的背景文档」
- prompt 标签改为 `【完整大纲（背景参考，把握整体方向，严格以本章大纲为准）】`
- 前端 Config / Outline 页标签同步

#### 4. 摘要系统重构
- **字数硬截断**：新增 500 汉字代码层截断，不靠 AI 自觉
- **PreviousEnding 精简**：从写作 prompt 中移除（省 ~800 字/token/章），保留在一致性检查中（400 字限制）
- 写作规则第 5 条同步更新（引用上一章结尾 → 引用章末承接）

#### 5. 声明检索（章节大纲关键词索引）
- 独立 JSON 文件索引（`项目目录/.declarations/declarations.json`）
- 纯关键词搜索（不走向量，不跑 embedding）
- 写作页大纲显示区旁设 🔍 搜索按钮
- Agent 工具 `search_declarations`，会话中可主动搜索
- 搜索匹配带章号（`[第N章 标题] 内容`）
- **不自动注入**——用户搜了、要求注入才注入

#### 6. Skill 注入控制
- `agent.go` 加 `category` 过滤
- craft 类（`writing` category）不再自动注入 Agent chat 上下文
- 仅保留 `polish` 类自动注入

#### 7. 主干大纲位置寻址
- 新增 `get_narrative_position` agent 工具
- `formatNarrativePosition` 函数自动计算故事弧位置（开端/发展/高潮/结局）
- 系统提醒词注入当前章节在主干大纲中的位置信息

#### 8. 后端代码修复
- `PutChapterOutline` / `PostOutlineChapters` / `PutSkillToggle` 加 `ensureProject` 保护
- `PostChapterConfirm` 加 `broadcastProgress`，修复 doConfirm 竞态条件
- `EditChapterOutline` 允许编辑非 writing 状态章节

### 二、文档改造
- README / README.en 全部重写（本文件）

### 三、未完成
- 改动一·阶段二：craft 修订按钮（待数据驱动后实现）

---

## 与原版相同的功能

- **单文件运行**：一个二进制文件 + 一个浏览器，无需安装数据库或其他依赖
- **多项目管理**：每部小说一个独立项目，可随时切换、新建、删除
- **两阶段创作**：先生成全书大纲供你审核修订，确认后逐章写作
- **逐章审核**：每章生成后可确认、提修改意见，AI 定向修订而不影响其他章节
- **自动确认模式**：开启后 AI 自动逐章连写，无需手动逐章确认，可随时开关
- **结构化设定**：角色、世界观、组织、人物关系独立管理，写作时自动注入相关上下文；支持 AI 一键生成初始设定
- **关系图谱**：可视化展示角色 / 组织 / 世界观之间的关系网络
- **伏笔系统**：AI 规划伏笔方案，写作时注入活跃伏笔，完成后自动追踪埋设 → 推进 → 回收，超期未回收自动告警
- **事实核查**：每章写完自动做一致性检查，不通过自动重写
- **续写已有作品**：粘贴已有文本，AI 分析提取设定与章节摘要后接着往下写
- **去 AI 味**：内置润色技能，写作页一键对单章去 AI 味
- **全书优化**：完稿后一键诊断 → 一致性核查 → 生成优化工单 → 逐章自动修订（支持大上下文模型、按卷核查、修改前后 diff 对比）
- **技能系统**：内置写作技巧 / 润色技能可选启用，也支持项目级自定义技能
- **AI 助理**：内置聊天助理，可通过对话查询和修改项目的设定、大纲、章节（破坏性操作有多层防护）
- **实时流式输出**：生成过程逐字实时展示，附带日志面板和进度提示
- **断点续作**：进度随时落盘，关闭程序后重新打开自动恢复
- **导出**：一键导出全书 TXT，章节文件同时以 Markdown 保存在项目目录中
- **多语言**：每个项目可选择中文或英文，AI 提示词、生成正文、内置技能、Agent 系统提示全部按项目语言切换；前端界面语言可独立切换

## 快速开始

### 1. 获取程序

自行编译（见文末「开发」一节），或下载 Release 中的可执行文件。

### 2. 运行

```bash
./show-me-the-story /path/to/storys
# 或指定端口
./show-me-the-story -port 8080 /path/to/storys
```

### 3. 使用

1. 浏览器打开 `http://localhost:48090`
2. 创建项目 → 填写故事梗概/世界观/角色 → 点击「生成大纲」
3. 审核 AI 生成的大纲 → 确认进入写作阶段
4. AI 逐章生成 → 可确认、也可提修改意见让 AI 修订

> 首次运行需先在「API 配置」中填写 OpenAI 兼容接口的地址和密钥。

---

## 贡献者

- **拐子** — 产品方案、需求定义、设计决策
- **白泽** — 方案实施、代码实现、技术咨询

## 致谢

- 原始项目：[Show Me The Story](https://github.com/NousResearch/show-me-the-story) by Nous Research

## 许可

原始项目采用 [Apache 2.0](LICENSE) 许可。本改造版同样以 Apache 2.0 发布。
