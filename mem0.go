package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"path/filepath"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// Mem0Client — HTTP 客户端调用 Mem0 sidecar
// ---------------------------------------------------------------------------

var mem0Client *Mem0Client

// mem0EntityWeights 存放每20章计算的实体权重，供冷记忆检索使用
var mem0EntityWeights map[string]float64

type Mem0Client struct {
	baseURL string
	client  *http.Client
}

func initMem0() {
	if mem0Client != nil {
		return
	}
	mem0Client = &Mem0Client{
		baseURL: "http://127.0.0.1:49152",
		client: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// projectIDFromPath 从项目目录或 progressPath 提取项目 ID
func projectIDFromPath(path string) string {
	base := filepath.Base(path)
	if filepath.Ext(base) != "" {
		return filepath.Base(filepath.Dir(path))
	}
	return base
}

// ---------------------------------------------------------------------------
// 请求/响应结构
// ---------------------------------------------------------------------------

type mem0AddRequest struct {
	ProjectID  string   `json:"project_id"`
	Memory     string   `json:"memory"`
	NodeType   string   `json:"node_type"`
	Entities   []string `json:"entities"`
	Chapter    int      `json:"chapter"`
	Emotion    string   `json:"emotion,omitempty"`
	Importance float64  `json:"importance"`
	Category   string   `json:"category"`
}

type mem0SearchRequest struct {
	ProjectID       string             `json:"project_id"`
	Query           string             `json:"query"`
	TopK            int                `json:"top_k"`
	ExcludeChapters []int              `json:"exclude_chapters"`
	Weights         map[string]float64 `json:"weights,omitempty"`
	CurrentChapter  int                `json:"current_chapter"`
}

type mem0SearchResult struct {
	ID         int       `json:"id"`
	Memory     string    `json:"memory"`
	NodeType   string    `json:"node_type"`
	Chapter    int       `json:"chapter"`
	Entities   []string  `json:"entities"`
	Importance float64   `json:"importance"`
	Category   string    `json:"category"`
	Score      float64   `json:"score"`
}

type mem0SearchResponse struct {
	Results []mem0SearchResult `json:"results"`
}

type mem0MemoriesItem struct {
	ID         int       `json:"id"`
	Memory     string    `json:"memory"`
	NodeType   string    `json:"node_type"`
	Chapter    int       `json:"chapter"`
	Entities   []string  `json:"entities"`
	Importance float64   `json:"importance"`
	Category   string    `json:"category"`
	CreatedAt  string    `json:"created_at"`
}

type mem0MemoriesResponse struct {
	Memories []mem0MemoriesItem `json:"memories"`
	Total    int                `json:"total"`
}

type mem0EntityGraphEntity struct {
	Related       []string `json:"related"`
	MentionCount  int      `json:"mention_count"`
	LastSeen      int      `json:"last_seen"`
}

type mem0EntityGraphResponse struct {
	Entities map[string]mem0EntityGraphEntity `json:"entities"`
}

// ---------------------------------------------------------------------------
// 写入记忆
// ---------------------------------------------------------------------------

func Mem0Add(ctx context.Context, progressPath string, chapter int, memory, category string, importance float64, entities []string) bool {
	initMem0()
	req := mem0AddRequest{
		ProjectID:  projectIDFromPath(progressPath),
		Memory:     memory,
		NodeType:   "episodic",
		Entities:   entities,
		Chapter:    chapter,
		Importance: importance,
		Category:   category,
	}
	body, err := json.Marshal(req)
	if err != nil {
		return false
	}
	httpReq, err := http.NewRequestWithContext(ctx, "POST",
		mem0Client.baseURL+"/api/add", bytes.NewReader(body))
	if err != nil {
		return false
	}
	httpReq.Header.Set("Content-Type", "application/json")
	resp, err := mem0Client.client.Do(httpReq)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

// ---------------------------------------------------------------------------
// 检索记忆（含系统B人格prompt格式化）
// ---------------------------------------------------------------------------

func Mem0Search(progressPath string, query string, topK int, exclude []int, weights map[string]float64, currentChapter int) string {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

		req := mem0SearchRequest{
			ProjectID:       projectIDFromPath(progressPath),
			Query:           query,
			TopK:            topK,
			ExcludeChapters: exclude,
			Weights:         weights,
			CurrentChapter:  currentChapter,
		}
	body, err := json.Marshal(req)
	if err != nil {
		return ""
	}
	httpReq, err := http.NewRequestWithContext(ctx, "POST",
		mem0Client.baseURL+"/api/search", bytes.NewReader(body))
	if err != nil {
		return ""
	}
	httpReq.Header.Set("Content-Type", "application/json")
	resp, err := mem0Client.client.Do(httpReq)
	if err != nil {
		return ""
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return ""
	}
	var searchResp mem0SearchResponse
	if err := json.Unmarshal(raw, &searchResp); err != nil {
		return ""
	}
	if len(searchResp.Results) == 0 {
		return ""
	}

	var buf bytes.Buffer
	buf.WriteString("\n【冷记忆——全书重要叙事线索】\n")
	buf.WriteString("（已发生过的事实，供参考，不做创作决策）\n")

	// 主角线优先
	var mainLine, supportingLine strings.Builder
	mainCount := 0
	mainKeywords := map[string]bool{"主角": true, "男主": true, "女主": true}
	for _, r := range searchResp.Results {
		line := fmt.Sprintf("[第%d章] %s\n", r.Chapter, r.Memory)
		isMain := false
		for _, e := range r.Entities {
			if mainKeywords[e] {
				isMain = true
				break
			}
		}
		if isMain && mainCount < 10 {
			mainLine.WriteString(line)
			mainCount++
		} else {
			supportingLine.WriteString(line)
		}
	}
	if mainLine.Len() > 0 {
		buf.WriteString("\n【主角线·重要前情】\n")
		buf.WriteString(mainLine.String())
	}
	if supportingLine.Len() > 0 {
		buf.WriteString("【关联线索】\n")
		buf.WriteString(supportingLine.String())
	}

	// 系统B人格prompt footer
	buf.WriteString("\n（系统B：每个人的故事都值得被认真讲述。）\n")
	return buf.String()
}

// ---------------------------------------------------------------------------
// 选角机制：每20章更新实体权重
// ---------------------------------------------------------------------------

func Mem0UpdateWeights(projectDir string) map[string]float64 {
	initMem0()
	pid := projectIDFromPath(projectDir)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s/api/entity_graph/%s", mem0Client.baseURL, pid)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return nil
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil
	}
	var graphResp struct {
		Entities map[string]struct {
			Related      []string `json:"related"`
			MentionCount int      `json:"mention_count"`
			LastSeen     int      `json:"last_seen"`
		} `json:"entities"`
	}
	if err := json.Unmarshal(raw, &graphResp); err != nil {
		return nil
	}

	// 计算总提及次数
	totalMentions := 0
	for _, e := range graphResp.Entities {
		totalMentions += e.MentionCount
	}
	if totalMentions == 0 {
		return nil
	}

	// 按出现频率分配权重
	weights := make(map[string]float64)

	for name, e := range graphResp.Entities {
		freq := float64(e.MentionCount) / float64(totalMentions)
		if freq >= 0.3 {
			weights[name] = freq * 2.0 // 主角翻倍
		} else {
			weights[name] = freq
		}
	}

	// 存到全局，供后续搜索使用
	mem0EntityWeights = weights
	return weights
}

// ---------------------------------------------------------------------------
// 健康检查 / 列表 / 删除 / 实体图
// ---------------------------------------------------------------------------

func Mem0Health() bool {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, "GET", mem0Client.baseURL+"/health", nil)
	if err != nil {
		return false
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == 200
}

func Mem0ListMemories(projectDir string, limit, offset int) (*mem0MemoriesResponse, error) {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s/api/memories/%s?limit=%d&offset=%d",
		mem0Client.baseURL, projectIDFromPath(projectDir), limit, offset)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var result mem0MemoriesResponse
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func Mem0DeleteMemory(projectDir string, memID int) error {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s/api/memory/%s/%d",
		mem0Client.baseURL, projectIDFromPath(projectDir), memID)
	req, err := http.NewRequestWithContext(ctx, "DELETE", url, nil)
	if err != nil {
		return err
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return nil
}

func Mem0GetEntities(projectDir string) (map[string]interface{}, error) {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s/api/entity_graph/%s", mem0Client.baseURL, projectIDFromPath(projectDir))
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func Mem0Merge(projectDir string) (map[string]interface{}, error) {
	initMem0()
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	url := fmt.Sprintf("%s/api/merge/%s", mem0Client.baseURL, projectIDFromPath(projectDir))
	req, err := http.NewRequestWithContext(ctx, "POST", url, nil)
	if err != nil {
		return nil, err
	}
	resp, err := mem0Client.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, err
	}
	return result, nil
}
