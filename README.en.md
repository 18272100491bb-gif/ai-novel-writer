# Show Me The Story — AI Novel Writer (Baize Fork)

> Forked from NousResearch/show-me-the-story. Chinese: [README.md](README.md)

Same binary, same web UI, same API. What changed is listed below.

---

## Changes compared to original SMTS

| # | Area | What | Why |
|---|------|------|-----|
| 1 | **Memory engine** | Replaced `sentence_transformers` with `fastembed` + `onnxruntime` | RAM: ~800MB → ~200MB. Local model `BAAI/bge-small-zh-v1.5`, no external API |
| 2 | **Prompt architecture** | Restructured flat user prompt into three priority layers: 🔴core directive / 🟡constraint / 🟢reference. Separated system prompt (persona) from user prompt. Removed `WritingStyle` (covered by persona) | AI stopped confusing instruction levels |
| 3 | **Full outline role** | Relabeled from per-chapter instruction to background reference. Frontend labels synced | Won't leak future plot in early chapters |
| 4 | **Summary system** | Code-level 500-char hard truncation. Removed PreviousEnding from writing prompt (kept in consistency check, 400-char limit) | Consistent summary quality, saves ~400 chars/token per chapter |
| 5 | **Declaration search** | Standalone JSON keyword index (`project/.declarations/declarations.json`). No vectors, no embedding. 🔍 button on writing page. Agent tool `search_declarations`. Search on demand only — no auto-inject | Find past chapter outlines without paying for vector DB |
| 6 | **Skill injection** | craft-category skills (`writing`) no longer auto-inject into agent chat. Only `polish` stays auto. | Less prompt noise |
| 7 | **Narrative position** | `get_narrative_position` agent tool. `formatNarrativePosition` function. Current story-arc position injected into system prompt | Context for what stage the story is at |
| 8 | **Bug fixes** | `ensureProject` guards. `broadcastProgress` fix. Chapter outline editing allowed on non-writing-state chapters | More stable |

## TODO

- craft revision button (pending declaration search data)

---

- **GuaiZi** — design, decisions
- **Baize** — implementation

> Original: NousResearch/show-me-the-story · Apache 2.0
