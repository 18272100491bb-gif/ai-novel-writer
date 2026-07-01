# Show Me The Story — AI Novel Writer (Baize Fork)

> Based on [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story). Differences from the original:

| # | Original (nigh) | This Fork |
|---|-----------------|-----------|
| 1 | **No Mem0 narrative memory** | Added full Mem0 sidecar (mem0.go + Python FastAPI + BAAI/bge-small-zh-v1.5). Later replaced sentence_transformers→fastembed+onnxruntime, RAM ~800MB→~200MB |
| 2 | **Flat prompt**: StorySynopsis/HistorySummary/PreviousEnding/WritingStyle etc. injected without priority | **Three-tier injection**: 🔴core (chapter outline·POV·word count) > 🟡constraint (story-so-far·project guidance·foreshadows) > 🟢reference (full outline·characters·worldview·memory). Removed WritingStyle (covered by persona). PreviousEnding moved to consistency check only |
| 3 | **StorySynopsis labeled "story synopsis"**, treated as per-chapter instruction | Relabeled "Full outline (reference)", frontend synced. AI per-chapter outline kept. Users can upload their own full outline — both layers coexist |
| 4 | **Summary word count left to AI** | Code-level 500-char hard truncation |
| 5 | **No chapter-outline keyword search** | Added `.declarations/declarations.json` keyword index, 🔍 search on writing page + `search_declarations` agent tool, on-demand only |
| 6 | **No story-arc awareness** | Added `get_narrative_position` agent tool + current phase in system prompt |
| 7 | **craft skills and polish skills both auto-inject** | craft skills filtered, only polish auto-injects |
| 8 | **Missing ensureProject guards / doConfirm race / chapter outline edit restriction** | All fixed |

GuaiZi (design) · Baize (implementation)
