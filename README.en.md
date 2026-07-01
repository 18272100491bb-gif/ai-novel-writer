# Show Me The Story — AI Novel Writer (Baize Fork)

> Based on [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story). Differences from the original:

| # | Original (nigh) | This Fork |
|---|-----------------|-----------|
| 1 | **Native memory** (progress.json embedded) | Added Mem0 sidecar (mem0.go + Python FastAPI + BAAI/bge-small-zh-v1.5 local vector search). Later replaced sentence_transformers→fastembed+onnxruntime, RAM ~800MB→~200MB. Added `search_memories` agent tool, reworked retrieval for novel writing. Native memory kept, Mem0 layered on top |
| 2 | **System prompt hardcoded** (SystemPromptFor(lang, "author_default")) | Replaced with `persona.txt` file override (project-level custom writing persona, falls back to default). System prompt and user prompt responsibilities fully separated |
| 3 | **User prompt flat-injected**: StorySynopsis/HistorySummary/PreviousEnding/WritingStyle etc. mixed without priority | **Three-tier injection**: 🔴core directive (chapter outline·POV·word count) > 🟡constraint (story-so-far·project guidance·foreshadows) > 🟢reference (full outline·characters·worldview·memory). Removed WritingStyle (covered by persona.txt). PreviousEnding moved to consistency check only |
| 4 | **StorySynopsis labeled "story synopsis"**, treated as per-chapter instruction | Relabeled "Full outline (reference)", frontend synced. Per-chapter AI-generated outline kept. Users can upload their own full outline — both layers coexist |
| 5 | **Summary word count left to AI** | Code-level 500-char hard truncation |
| 6 | **No chapter-outline keyword search** | Added `.declarations/declarations.json` keyword index, 🔍 search on writing page + `search_declarations` agent tool, on-demand only |
| 7 | **No story-arc awareness** | Added `get_narrative_position` agent tool + current phase in system prompt |
| 8 | **craft and polish skills both auto-inject** | craft filtered, only polish auto-injects |
| 9 | **Missing ensureProject guards / doConfirm race / chapter outline edit restriction** | All fixed |

GuaiZi (design) · Baize (implementation)
