package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// OutlineParseResult 从完整大纲中提取的设定信息
type OutlineParseResult struct {
	Characters    []Character              `json:"characters"`
	Worldview     []WorldviewEntry         `json:"worldview"`
	Organizations []Organization           `json:"organizations"`
	Foreshadows   []OutlineParseForeshadow `json:"foreshadows"`
	Relations     []OutlineParseRelation   `json:"relations"`
}

type OutlineParseForeshadow struct {
	Name          string `json:"name"`
	Description   string `json:"description"`
	PlantChapter  int    `json:"plant_chapter"`
	TargetChapter int    `json:"target_chapter"`
}

type OutlineParseRelation struct {
	Source   string `json:"source"`
	Target   string `json:"target"`
	Label    string `json:"label"`
	Relation string `json:"relation"`
}

// ParseOutlineAction 从完整大纲中提取角色/世界观/组织/伏笔/关系，写入 settings 和 state。
func ParseOutlineAction(ctx context.Context, apiCfg *APIConfig, cfg *Config, state *Progress, settings *ProjectSettings, logger *LogBroadcaster) error {
	if err := validateAPIConfig(apiCfg); err != nil {
		return err
	}

	synopsis := state.StorySynopsis
	if strings.TrimSpace(synopsis) == "" {
		synopsis = cfg.Story.StorySynopsis
	}
	if strings.TrimSpace(synopsis) == "" {
		return fmt.Errorf("没有完整大纲可解析")
	}

	lang := cfg.Language
	userPrompt := RenderPrompt(cfg.Prompts.OutlineParse, map[string]string{
		"FullSynopsis": synopsis,
	})
	systemPrompt := SystemPromptFor(lang, "outline_editor_json")

	resp := CallAPIWithRetryLog(ctx, apiCfg, systemPrompt, userPrompt, logger)
	if resp == "" {
		return fmt.Errorf("大纲解析调用失败或被取消")
	}

	result, err := parseOutlineParseResult(resp)
	if err != nil {
		return fmt.Errorf("解析AI返回结果失败: %w", err)
	}

	// 建立名称→ID映射（角色+组织），用于后续关联关系
	nameToID := make(map[string]string)

	// 写入角色设定
	if len(result.Characters) > 0 {
		for i := range result.Characters {
			id := "char_" + strconv.Itoa(i+1)
			result.Characters[i].ID = id
			nameToID[result.Characters[i].Name] = id
		}
		settings.Characters = result.Characters
	}

	// 写入世界观
	if len(result.Worldview) > 0 {
		for i := range result.Worldview {
			result.Worldview[i].ID = "wv_" + strconv.Itoa(i+1)
		}
		settings.Worldview = result.Worldview
	}

	// 写入组织
	if len(result.Organizations) > 0 {
		for i := range result.Organizations {
			id := "org_" + strconv.Itoa(i+1)
			result.Organizations[i].ID = id
			nameToID[result.Organizations[i].Name] = id
			// 组织成员用名称匹配到角色ID
			if len(result.Organizations[i].Members) > 0 {
				mapped := make([]string, 0, len(result.Organizations[i].Members))
				for _, m := range result.Organizations[i].Members {
					if id, ok := nameToID[m]; ok {
						mapped = append(mapped, id)
					} else {
						// 未匹配到的角色名保留原样
						mapped = append(mapped, m)
					}
				}
				result.Organizations[i].Members = mapped
			}
		}
		settings.Organizations = result.Organizations
	}

	// 写入关系（用名称匹配角色/组织的ID）
	if len(result.Relations) > 0 {
		var rels []Relation
		for i, r := range result.Relations {
			srcID := r.Source
			if id, ok := nameToID[r.Source]; ok {
				srcID = id
			}
			tgtID := r.Target
			if id, ok := nameToID[r.Target]; ok {
				tgtID = id
			}
			relLabel := r.Label
			if relLabel == "" {
				relLabel = r.Relation
			}
			rels = append(rels, Relation{
				ID:         strconv.Itoa(i + 1),
				SourceID:   srcID,
				SourceType: inferEntityType(srcID),
				TargetID:   tgtID,
				TargetType: inferEntityType(tgtID),
				Label:      relLabel,
			})
		}
		settings.Relations = rels
	}

	// 写入伏笔
	if len(result.Foreshadows) > 0 {
		var foreshadows []Foreshadow
		for i, f := range result.Foreshadows {
			foreshadows = append(foreshadows, Foreshadow{
				ID:            i + 1,
				Name:          f.Name,
				Description:   f.Description,
				PlantChapter:  f.PlantChapter,
				TargetChapter: f.TargetChapter,
				Status:        ForeshadowPlanted,
			})
		}
		state.Foreshadows = foreshadows
	}

	logger.SuccessKey("log.outline_parse_done",
		len(result.Characters), len(result.Worldview),
		len(result.Organizations), len(result.Foreshadows))

	return nil
}

// inferEntityType 根据ID前缀推断实体类型
func inferEntityType(id string) string {
	if strings.HasPrefix(id, "char_") {
		return "character"
	}
	if strings.HasPrefix(id, "org_") {
		return "organization"
	}
	return "unknown"
}

func parseOutlineParseResult(raw string) (*OutlineParseResult, error) {
	cleaned := cleanJSONResponse(raw)
	var result OutlineParseResult
	if err := json.Unmarshal([]byte(cleaned), &result); err != nil {
		return nil, fmt.Errorf("解析JSON失败: %w\n原始响应: %s", err, raw)
	}
	return &result, nil
}

// hasStructuredData 检查各接口是否有数据。
// 角色/世界观/组织任意一个有数据就算"已填充"，不再需要完整大纲兜底。
func hasStructuredData(state *Progress, settings *ProjectSettings) bool {
	if settings == nil {
		return false
	}
	if len(settings.Characters) > 0 || len(settings.Worldview) > 0 || len(settings.Organizations) > 0 {
		return true
	}
	return false
}
