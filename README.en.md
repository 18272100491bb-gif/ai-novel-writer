# Show Me The Story — AI Novel Writer (Baize Fork)

> Based on [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story) with deep modifications.
> Listed below are the main differences from the original. Features not listed remain unchanged.

A self-hosted long-form novel AI writing tool. Single binary, built-in Web UI, connects to any OpenAI-compatible API.

## Key Differences from Upstream

### Memory System

| Aspect | Original | This Fork |
|--------|----------|-----------|
| Storage | progress.json embedded, no vector search | **Dual-track**: track 1 (hot) keeps native progress.json per-chapter snippets; track 2 (cold) Mem0 Sidecar + BAAI/bge-small-zh-v1.5 local vector search |
| Retrieval | None | SQLite + FTS full-text + BM25 + semantic vector + entity graph, fused ranking |
| Weighting | None | Entity re-weighting every 20 chapters ("casting" mechanism) |
| Fault tolerance | N/A | Graceful degradation to native memory when Mem0 is down |
| Agent tool | None | `search_memories` conversational retrieval tool |

### Writing Persona

Original system prompt was flat: "You are a novelist. Output only the story body."

Rewritten as **three-tier persona architecture**:

- **Top**: identity & values (young writer with ideas, rigorous but not dogmatic)
- **Middle**: expression preferences (show > tell, meme-savvy without being literary, no filler)
- **Bottom**: hard rules (no meta-info, consistent POV)

Overridable via `persona.txt` file. Persona also gates how retrieved memories are interpreted ("casting" linkage).

### Prompt Tiering

Original: flat injection of StorySynopsis / HistorySummary / PreviousEnding / WritingStyle etc.

**Three-tier injection**:

- 🔴 **Core directive**: chapter outline · POV · word count
- 🟡 **Constraints**: story-so-far · project guidance · foreshadows
- 🟢 **Reference**: full outline · characters · worldview · memory

WritingStyle removed (covered by persona). PreviousEnding moved to consistency check only.

### Acceptance Check

Original: single-dimension fact check with retry loop (up to 3 attempts + conflict analysis).

**Three-dimension one-shot check**:

| Dimension | Rules |
|-----------|-------|
| Fact check | Original 6 rules (character/setting/timeline/causality/ability/logic) |
| Gate 7 Emotional redundancy | 7 rules: repeated emotion/no new info, abstract emotion wrapping action, emotional summary after scene description, emotion already expressed by action+repeated in thoughts, cliché emotional metaphors, justification after explicit statement, cross-paragraph repetition |
| Gate 8 Rhetorical awareness | 5 rules: tone matching scene, rhetoric intensity matching scene, density in same paragraph, character-appropriate rhetoric, narrative purpose |

Result: GateReports[] stored per chapter, frontend shows PASS/FAIL + issue list.
One API call for all 3 dimensions → issues aggregated → one-shot revision → no re-verification loop.

### Generation Flow

Original: generate → summary → fact-check (loop) → foreshadow sync → memory sync → review

This fork: generate → 3-dimension check → optional revision → **review (awaiting user)** → user confirms → async: summary → foreshadow sync → memory sync → accepted

Summary, foreshadow sync, memory sync moved to confirmation phase.

### Outline Handling

Original: StorySynopsis treated as per-chapter writing instruction, injected directly into prompt.

**Fork architecture**: full outline uploaded → `/api/outline/parse` → AI extracts to character/worldview/organization/relationship/foreshadow interfaces. Generate-time check: interfaces have data → skip full outline injection; empty → fallback to full outline.

### Other Changes

| # | Original | This Fork |
|---|----------|-----------|
| 1 | No hard limit on summary length | Code-level 500-char truncation |
| 2 | No chapter outline keyword search | `.declarations/declarations.json` index + Agent `search_declarations` tool |
| 3 | No narrative position awareness | `get_narrative_position` Agent tool + system prompt injection |
| 4 | Craft and polish skills auto-injected equally | Craft skills filtered, only polish auto-injected |
| 5 | Backend missing ensureProject/doConfirm-race/outline-edit fixes | All fixed |
| 6 | Confirm synchronous (just mark accepted) | Async (summary+foreshadow+memory in background) |
| 7 | story-deslop: 6-Gate detection | Upgraded to 7-Gate (added emotional redundancy) |
| 8 | — | New: outline_parse.go for structured outline extraction |

## Highlights

- **Single binary** – no database or external dependencies
- **Multi-project management** – each novel an independent project
- **Two-phase creation** – full outline → per-chapter writing with review
- **Three-dimension acceptance** – fact check + emotional redundancy + rhetorical awareness
- **Dual-track memory** – Mem0 vector search layered on native progress.json
- **Persona system** – three-tier architecture, overridable via `persona.txt`
- **Prompt tiering** – core/constraints/reference layered injection
- **Foreshadow tracking** – auto-planted, tracked, notified on overdue resolution
- **Full-novel optimization** – diagnostic → consistency check → work order → auto-revision
- **AI assistant** – conversational agent with multi-layered safety
- **Real-time streaming** – word-by-word display during generation
- **Auto-confirm mode** – hands-free consecutive chapter generation
- **Multi-language** – CN/EN project-level switching
- **Outline parsing** – full outline → structured data extraction

## Quick Start

### 1. Get the binary

Download from releases, or build from source (see Development below).

### 2. Run

```bash
./show-me-the-story
```

Visit `http://localhost:48090`.

### 3. Configure API

Fill in API URL, model name, API key on the Config page.

### 4. Start writing

1. Configure story type, chapter count, word count
2. Generate outline → review/edit
3. Generate chapters → review acceptance reports → confirm or revise
4. Enable auto-confirm for uninterrupted generation

## Development

```bash
git clone https://github.com/18272100491bb-gif/ai-novel-writer.git
cd show-me-the-story
go build -o show-me-the-story .
```

Frontend:

```bash
cd frontend
npm install
npm run dev    # dev mode with HMR
npm run build  # production build
```
