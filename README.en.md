# Show Me The Story — AI Novel Writer (Baize Fork)

> Original by nigh · MIT. Differences from the original:

| # | Original | This Fork |
|---|----------|-----------|
| 1 | StorySynopsis injected as per-chapter instruction | Relabeled "Full outline (reference)". Per-chapter AI-generated outline kept. Users can upload their own full outline. Both layers coexist |
| 2 | Flat prompt, no priority | Three-tier injection: 🔴core directive > 🟡constraint > 🟢reference |
| 3 | WritingStyle as standalone field | Removed (covered by persona) |
| 4 | Previous 800 chars of last chapter injected into writing prompts | Removed from writing prompt (kept in consistency check, 400 chars) |
| 5 | Summary left to AI | Code-level 500-char hard truncation |
| 6 | No chapter-outline search | `.declarations/declarations.json` keyword index, 🔍 search on writing page + agent tool, on-demand only |
| 7 | Mem0 uses sentence_transformers | Replaced with fastembed+onnxruntime (BAAI/bge-small-zh-v1.5, local no external API). RAM ~800MB→~200MB. Sidecar deployment. Frontend retry protection |
| 8 | craft skills auto-inject to Agent | Filtered, only polish auto-injects |
| 9 | No story-arc awareness | get_narrative_position tool + system prompt |
| 10 | Missing ensureProject guards / doConfirm race / outline edit restriction | All fixed |

GuaiZi (design/decisions) · Baize (implementation)
