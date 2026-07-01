# Show Me The Story — AI Novel Writer (Baize Fork)

> Forked from [NousResearch/show-me-the-story](https://github.com/NousResearch/show-me-the-story)
>
> 中文文档: [README.md](README.md)

An out-of-the-box long-form novel AI writing tool. Single binary, full web UI, works with any OpenAI-compatible API.

**This fork's core redesign was led by @BaiTuo (GuaiZi) and implemented by Baize (AI).** Differences from the original are listed below.

---

## Key Modifications (vs original SMTS)

### Prompt Architecture — Three-tier priority
- Writing prompts restructured from flat injection to three priority layers:
  - **🔴 Core directives** (chapter outline · narrative POV · word count) — must follow strictly
  - **🟡 Constraints** (story-so-far · foreshadows · project guidance) — must not contradict
  - **🟢 Reference** (full outline · characters · worldview · memory) — directional background
- System prompt (persona) and user prompt responsibilities fully separated
- WritingStyle removed (covered by persona)

### Full Outline → Background Reference
- Original SMTS treats "story synopsis" as per-chapter instruction
- Fork repositions the full outline as a "directional background document", labeled `[Full outline (reference)]`
- Frontend Config / Outline page labels synced

### Summary System
- Hard 500-character code-level truncation (not soft prompt)
- PreviousEnding (previous chapter's tail) removed from writing prompt — saves ~400 chars/token per chapter
- PreviousEnding kept in consistency check (400-char limit) with `[Reference]` label

### Declaration Search (Chapter Outline Index)
- Standalone JSON index (`project/.declarations/declarations.json`)
- Pure keyword search (no vectors, no embedding)
- 🔍 Search button on writing page next to outline display
- `search_declarations` agent tool available in chat
- No auto-injection — user searches and decides whether to inject

### Other Changes
- Removed OutlineConstraints empty-loop from writing.go
- Frontend i18n fully synced with all label changes

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
- **Narrative memory (Mem0)**: extracts unplanned details, cross-chapter injection
- **Fact checking**: auto consistency check per chapter, auto-rewrite on failure
- **Continue existing works**: paste existing text → AI analyzes and continues
- **De-AI-ify**: built-in polish skills to remove AI-isms
- **Full novel optimization**: diagnosis → consistency → work orders → auto-revision
- **Skill system**: built-in writing/polish skills, project-level custom skills
- **AI assistant**: chat-based project management via conversation
- **Real-time streaming**: character-by-character output
- **Checkpoint resume**: progress saved on every write
- **Export**: single-file TXT + per-chapter Markdown
- **Multi-language**: per-project ZH/EN switching

## Quick Start

### 1. Get the binary

Build from source (see "Development" below), or download from Releases.

### 2. Run

```bash
./show-me-the-story /path/to/storys

# Custom port
./show-me-the-story -port 8080 /path/to/storys
```

### 3. Use

1. Open `http://localhost:48090`
2. Create project → set story synopsis/characters/world → click "Generate outline"
3. Review AI outline → confirm to enter writing phase
4. AI writes chapter by chapter → review, revise, confirm

> First-time setup: configure API endpoint and key in the settings page (supports DeepSeek, OpenRouter, Ollama, LM Studio, etc.)

---

## Contributors

- **@BaiTuo (GuaiZi)** — product design, requirements, decisions
- **Baize (AI)** — implementation, coding, technical consulting

## Credits

- Original project: [Show Me The Story](https://github.com/NousResearch/show-me-the-story) by Nous Research

## License

Original project is [Apache 2.0](LICENSE). This fork is also released under Apache 2.0.
