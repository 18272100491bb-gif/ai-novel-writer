# Show Me The Story — AI Novel Writer (Baize Fork)

> Forked from NousResearch/show-me-the-story. This fork differs from the original in the following ways.

| # | Original | This Fork |
|---|----------|-----------|
| 1 | StorySynopsis injected as per-chapter instruction | Relabeled as "Full outline (reference)" — directional only, per-chapter outline takes precedence. Frontend labels synced |
| 2 | All prompt fields flat-injected, no priority | Three-tier injection: 🔴core directive > 🟡constraint > 🟢reference |
| 3 | WritingStyle as a standalone field | Removed (covered by persona) |
| 4 | Previous 800 chars of last chapter injected into every writing call (PreviousEnding) | Removed from writing prompt (kept in consistency check, 400-char limit) |
| 5 | Summary word count left to AI's discretion | Code-level 500-char hard truncation |
| 6 | No chapter-outline search | `.declarations/declarations.json` keyword index. 🔍 search button on writing page + agent tool. On-demand only |
| 7 | Mem0 uses sentence_transformers | Replaced with fastembed + onnxruntime. RAM ~800MB→~200MB |
| 8 | craft-category skills auto-inject into Agent chat | Filtered — only polish skills auto-inject |
| 9 | No story-arc awareness | get_narrative_position tool + current phase info in system prompt |

### Contributors

GuaiZi (design/decisions) · Baize (implementation)

> Original: NousResearch/show-me-the-story · Apache 2.0
