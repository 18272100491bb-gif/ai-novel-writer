# Show Me The Story — AI Novel Writer (Baize Fork)

> Forked from NousResearch/show-me-the-story
> 中文文档: [README.md](README.md)

Long-form novel AI writing tool. Single binary, web UI, works with any OpenAI-compatible API.

This fork focuses on: **removing redundancy, clarifying hierarchy, hard code-level constraints.**

---

## Changelog

### ✅ Done

| # | Change | Effect |
|---|--------|--------|
| 1 | Mem0 memory: sentence_transformers→fastembed | ~800MB→~200MB RAM |
| 2 | Prompt three-tier priority | AI no longer confuses instruction levels |
| 3 | Full outline→background reference | Won't leak future plot in early chapters |
| 4 | Summary hard-truncated at 500 chars | Stable summary length |
| 5 | PreviousEnding removed from writing prompt (kept in consistency check, 400 chars) | ~400 chars/token saved per chapter |
| 6 | Declaration search: standalone JSON index, keyword-only | No vectors, no embedding |
| 7 | Skill injection filter: craft skills no longer auto-inject | Less prompt noise |
| 8 | get_narrative_position tool | Story-arc awareness |
| 9 | Backend fixes: race condition / ensureProject / editing restriction | More stable |

### ⬜ TODO

- craft revision button (pending declaration search data)

---

## Quick Start

```bash
./show-me-the-story /path/to/storys
```

Open `http://localhost:48090` → create project → set world → generate outline → write.

First-time: configure API endpoint + key in settings (supports DeepSeek / OpenAI / Ollama / LM Studio).

---

- **GuaiZi** — design & decisions
- **Baize** — implementation

> Original: NousResearch/show-me-the-story · Apache 2.0
