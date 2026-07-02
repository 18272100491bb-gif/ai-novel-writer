# Show Me The Story · Baize Fork

> A deep fork of [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story), focusing on three pain points in AI novel writing: **memory continuity**, **natural prose**, and **closed-loop acceptance**.

## Key Improvements

### 🧠 Dual-Track Narrative Memory

The original project relies on prompt-level history compression — details degrade quickly as chapters pile up.

We introduce a Mem0 sidecar with local embeddings for a **hot/cold dual-track architecture**:

- **Hot memory**: original progress.json per-chapter snippets, instantly available
- **Cold memory**: Mem0 + BGE local vector search, triggered every 5 chapters with fused ranking (BM25 + embedding + entity weight + proximity boost)

Entity weights are recalculated every 20 chapters — keeping the model focused on active characters rather than one-off extras. Graceful degradation to native memory when Mem0 is unavailable.

### 🎭 Three-Tier Writing Persona

The original system prompt was a single flat rule. We replaced it with a layered persona:

| Layer | Purpose | Role |
|-------|---------|------|
| **Top** | Identity & values | Defines the AI's self-concept |
| **Middle** | Expression preferences | Show > tell, high information density, no filler |
| **Bottom** | Hard constraints | No meta-output, consistent POV |

Customizable via `persona.txt`. The persona also acts as a memory filter — the same retrieved facts are interpreted differently depending on the active persona ("casting linkage").

### 📐 Three-Tier Prompt Injection

Original: flat injection of synopsis, history, style, characters, worldview — no priority, the model gets lost.

Three tiers by priority:

```
🔴 Core directive   → chapter outline · POV · word count
🟡 Constraints      → story-so-far · project guidance · active foreshadows
🟢 Reference        → full outline · characters · worldview · memory
```

WritingStyle removed (covered by persona). PreviousEnding moved to consistency check only.

### ✅ Three-Dimension Acceptance Check

Original: single-dimension fact check with retry loop (check → rewrite → recheck → loop).

We replaced it with a **one-shot three-dimension check**:

| Dimension | Rules | What it checks |
|-----------|-------|----------------|
| **Fact check** | 6 | Character/setting/timeline/causality/ability/logic consistency |
| **Gate 7 · Emotional redundancy** | 7 | Repeated emotion, abstract emotion wrapping action, post-scene emotional summary, unnecessary inner monologue, cliché metaphors |
| **Gate 8 · Rhetorical awareness** | 5 | Tone matching, density control, character-appropriate rhetoric |

Issues are aggregated into one revision pass — no loop, no re-verification. Gate reports are stored per-chapter and displayed in the UI as PASS/FAIL with issue details.

### 🔄 Optimized Generation Flow

Original: generate → summary → fact-check (loop) → foreshadow sync → memory sync → review

Wasteful when the user wants to revise before confirming.

Adjusted flow:

```
generate → 3D check → optional revision → mark review
                                            ↓ user confirms
                                    async: summary → foreshadow → memory → accepted
```

Summary, foreshadow sync, and memory sync are deferred to confirmation — saving at least one API round trip.

### 📋 Outline Fork Architecture

Original: full outline injected directly into the generation prompt — prompt bloat.

We introduced `/api/outline/parse`: full outline is extracted into five structured interfaces (characters / worldview / organizations / relationships / foreshadows). During generation: if interfaces have data → skip full outline injection; if empty → fallback to full outline. Both layers coexist.

### Other Improvements

- **500-char hard truncation** on summaries — code-level, not AI self-discipline
- **Keyword search**: `.declarations/declarations.json` index, on-demand, no auto-injection
- **Narrative position awareness**: agent knows which story phase is active (beginning / development / climax / resolution)
- **Skill filtering**: craft-type skills filtered, only polish auto-injected
- **Backend stability**: fixed nil-pointer, race conditions, outline permission issues
- **Async confirmation**: chapter confirmation runs in background, non-blocking

## Quick Start

```bash
git clone <repo-url>
cd show-me-the-story
go build -o show-me-the-story .
./show-me-the-story
```

Visit `http://localhost:48090`.

Frontend development:

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

- **Backend**: Go (single binary)
- **Frontend**: Svelte 4 + Vite
- **Memory**: Mem0 + BAAI/bge-small-zh-v1.5 (local, no external API calls)
- **API**: Any OpenAI-compatible endpoint

## Acknowledgements

Thanks to [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story) for the excellent foundation.
