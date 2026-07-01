# Show Me The Story — AI Novel Writer (Baize Fork)

> Forked from [NousResearch/show-me-the-story](https://github.com/NousResearch/show-me-the-story)
>
> 中文文档: [README.md](README.md)

An out-of-the-box long-form novel AI writing tool. Single binary, full web UI, works with any OpenAI-compatible API (DeepSeek, OpenAI, Ollama, LM Studio, etc.).

---

## Modifications (vs original SMTS)

### 1. Mem0 Narrative Memory Engine Optimization
- **Replaced embedding library**: `sentence_transformers` → `fastembed` (TextEmbedding) + `onnxruntime`
- **Result**: Memory usage dropped from ~800MB to ~200MB, zero external dependencies
- **Local model**: `BAAI/bge-small-zh-v1.5`, no external API calls
- **Mem0 sidecar**: Independent Python FastAPI process (port 49152), decoupled from Go backend

### 2. Prompt Architecture — Three-tier Priority
- Writing prompts restructured from flat injection to three priority layers:
  - **🔴 Core directives** (chapter outline · narrative POV · word count) — must follow strictly
  - **🟡 Constraints** (story-so-far · foreshadows · project guidance) — must not contradict
  - **🟢 Reference** (full outline · characters · worldview · narrative memory) — directional background
- System prompt (persona) and user prompt responsibilities fully separated
- Removed `WritingStyle` (now covered by persona) and `PreviousEnding` from writing prompt

### 3. Full Outline → Background Reference
- Original SMTS treats StorySynopsis as per-chapter instruction
- Fork repositions full outline as a "directional background document"
- Prompt label changed to `[Full outline (reference)]`
- Frontend Config / Outline page labels synced

### 4. Summary System Refactored
- **Hard character limit**: 500-char code-level truncation (not soft prompt)
- **PreviousEnding trimmed**: Removed from writing prompt (saves ~400 chars/token per chapter), kept in consistency check (400-char limit)

### 5. Declaration Search (Chapter Outline Keyword Index)
- Standalone JSON index (`project/.declarations/declarations.json`)
- Pure keyword search (no vectors, no embedding)
- 🔍 Search button on writing page next to outline display
- `search_declarations` agent tool, accessible in chat
- Results tagged with chapter number (`[Ch.N Title] content`)
- **No auto-injection** — user searches and decides whether to inject

### 6. Skill Injection Control
- `agent.go` category filter: craft-level (`writing` category) skills no longer auto-inject into Agent chat
- Only `polish` category remains auto-injectable

### 7. Narrative Position Tool
- `get_narrative_position` agent tool added
- `formatNarrativePosition` function computes story arc position (beginning/rising/climax/resolution)
- System prompt informed of current position in the full outline

### 8. Backend Bug Fixes
- `PutChapterOutline` / `PostOutlineChapters` / `PutSkillToggle` — added `ensureProject` guard
- `PostChapterConfirm` — added `broadcastProgress`, fixed doConfirm race condition
- `EditChapterOutline` — allowed editing non-writing-state chapters

### 9. Documentation
- README / README.en fully rewritten (this file)

---

## Features Carried Over from Original

- **Single-file operation**: one binary + browser, no database or external deps
- **Multi-project management**: independent projects per novel
- **Two-phase creation**: outline generation → chapter-by-chapter writing
- **Per-chapter review**: confirm, request revisions, targeted AI edits
- **Auto-confirm mode**: hands-free continuous chapter generation
- **Structured settings**: characters, worldbuilding, organizations, relationships
- **Relationship graph**: visual character/org/world network
- **Foreshadowing system**: AI-planned, tracked from planting → progression → resolution
- **Fact checking**: auto consistency check per chapter, auto-rewrite on failure
- **Continue existing works**: paste existing text → AI analyzes and continues
- **De-AI-ify**: built-in polish skills to remove AI-isms
- **Full novel optimization**: diagnosis → consistency → work orders → auto-revision
- **Skill system**: built-in writing/polish skills, project-level custom skills
- **AI assistant**: chat-based project management via conversation
- **Real-time streaming**: character-by-character output
- **Checkpoint resume**: progress saved on every write
- **Export**: single-file TXT + per-chapter Markdown
- **Multi-language**: per-project ZH/EN switching (prompts, content, skills, agent)

## Quick Start

```bash
./show-me-the-story /path/to/storys
# Custom port
./show-me-the-story -port 8080 /path/to/storys
```

Open `http://localhost:48090`, create a project, configure API, generate outline, start writing.

---

## Contributors

- **GuaiZi** — product design, requirements, decision-making
- **Baize** — implementation, coding, technical consulting

## Credits

- Original project: [Show Me The Story](https://github.com/NousResearch/show-me-the-story) by Nous Research

## License

Original project is [Apache 2.0](LICENSE). This fork is also released under Apache 2.0.
