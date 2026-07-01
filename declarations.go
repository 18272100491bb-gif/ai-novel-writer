package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

// DeclarationDB manages keyword-searchable chapter outline declarations.
// Stored as a JSON file in <projectDir>/.declarations/declarations.json.
// No FTS5, no vector DB — pure keyword match on a small dataset (≤200 entries).

type DeclarationEntry struct {
	ChapterNum   int    `json:"chapter_num"`
	ChapterTitle string `json:"chapter_title"`
	Content      string `json:"content"`
}

type DeclarationDB struct {
	mu       sync.RWMutex
	filePath string
	entries  []DeclarationEntry
}

// OpenDeclarationDB opens (or creates) the declaration store for a project.
func OpenDeclarationDB(projectDir string) (*DeclarationDB, error) {
	dir := filepath.Join(projectDir, ".declarations")
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("create declarations dir: %w", err)
	}
	db := &DeclarationDB{
		filePath: filepath.Join(dir, "declarations.json"),
	}
	_ = db.load() // ignore error on first use (file doesn't exist yet)
	return db, nil
}

func (d *DeclarationDB) load() error {
	d.mu.Lock()
	defer d.mu.Unlock()
	data, err := os.ReadFile(d.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			d.entries = nil
			return nil
		}
		return err
	}
	return json.Unmarshal(data, &d.entries)
}

func (d *DeclarationDB) save() error {
	data, err := json.MarshalIndent(d.entries, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(d.filePath, data, 0644)
}

// SyncChapter writes (or updates) a single chapter's declaration.
func (d *DeclarationDB) SyncChapter(num int, title, content string) error {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Update existing or append
	for i, e := range d.entries {
		if e.ChapterNum == num {
			d.entries[i].ChapterTitle = title
			d.entries[i].Content = content
			return d.save()
		}
	}
	d.entries = append(d.entries, DeclarationEntry{
		ChapterNum:   num,
		ChapterTitle: title,
		Content:      content,
	})
	return d.save()
}

// DeleteChapter removes a chapter's declaration.
func (d *DeclarationDB) DeleteChapter(num int) error {
	d.mu.Lock()
	defer d.mu.Unlock()
	for i, e := range d.entries {
		if e.ChapterNum == num {
			d.entries = append(d.entries[:i], d.entries[i+1:]...)
			return d.save()
		}
	}
	return nil
}

// SearchResult represents one matching declaration.
type DeclarationResult struct {
	ChapterNum   int    `json:"chapter_num"`
	ChapterTitle string `json:"chapter_title"`
	Content      string `json:"content"`
}

// Search does simple keyword matching (case-insensitive substring) on all entries.
// Small dataset (<200 entries) makes brute-force fast enough.
func (d *DeclarationDB) Search(query string) []DeclarationResult {
	d.mu.RLock()
	defer d.mu.RUnlock()

	q := strings.ToLower(strings.TrimSpace(query))
	if q == "" {
		return nil
	}

	var results []DeclarationResult
	for _, e := range d.entries {
		if strings.Contains(strings.ToLower(e.Content), q) ||
			strings.Contains(strings.ToLower(e.ChapterTitle), q) {
			results = append(results, DeclarationResult{
				ChapterNum:   e.ChapterNum,
				ChapterTitle: e.ChapterTitle,
				Content:      e.Content,
			})
		}
	}
	return results
}

// SyncAllFromState rebuilds the entire store from Progress data.
func (d *DeclarationDB) SyncAllFromState(state *Progress) error {
	var entries []DeclarationEntry
	for _, ch := range state.Chapters {
		if strings.TrimSpace(ch.Outline) != "" {
			entries = append(entries, DeclarationEntry{
				ChapterNum:   ch.Num,
				ChapterTitle: ch.Title,
				Content:      ch.Outline,
			})
		}
	}
	d.mu.Lock()
	d.entries = entries
	err := d.save()
	d.mu.Unlock()
	return err
}

// FormatDeclarations formats matched declarations as a readable text block.
func FormatDeclarations(results []DeclarationResult) string {
	if len(results) == 0 {
		return ""
	}
	var sb strings.Builder
	for _, r := range results {
		sb.WriteString(fmt.Sprintf("[第%d章 %s] %s\n", r.ChapterNum, r.ChapterTitle, r.Content))
	}
	return sb.String()
}
