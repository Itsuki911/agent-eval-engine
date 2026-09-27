package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	maxTraceBytes  = 5 * 1024 * 1024 // 5 MiB
	maxTraceEvents = 10000
)

// トレース検証結果を表す
type traceValidationResult struct {
	Status      string `json:"status"`
	AdapterType string `json:"adapter_type"`
	BenchmarkID string `json:"benchmark_id"`
	AgentName   string `json:"agent_name"`
	EventCount  int    `json:"event_count"`
	TaskSuccess bool   `json:"task_success"`
	FilePath    string `json:"file_path"`
}

// 辞書・値の中に秘密情報キーが含まれていないか再帰的に検査する
func checkSecrets(data any) error {
	switch v := data.(type) {
	case map[string]any:
		for k, val := range v {
			lowerKey := strings.ToLower(k)
			for _, secretKeyword := range []string{"api_key", "token", "password", "secret", "auth_header", "cookie"} {
				if strings.Contains(lowerKey, secretKeyword) {
					return fmt.Errorf("秘密情報キー (%s) が含まれています", k)
				}
			}
			if err := checkSecrets(val); err != nil {
				return err
			}
		}
	case []any:
		for _, item := range v {
			if err := checkSecrets(item); err != nil {
				return err
			}
		}
	}
	return nil
}

// JSONL トレースファイルを検証する
func validateTraceFile(path string) (traceValidationResult, error) {
	if filepath.Ext(path) != ".jsonl" {
		return traceValidationResult{}, fmt.Errorf("トレースファイルは .jsonl 拡張子を指定してください: %s", path)
	}

	info, err := os.Stat(path)
	if err != nil {
		return traceValidationResult{}, fmt.Errorf("ファイルが見つかりません: %w", err)
	}
	if info.Size() > maxTraceBytes {
		return traceValidationResult{}, fmt.Errorf("ファイルサイズが上限 (5 MiB) を超えています: %d bytes", info.Size())
	}

	file, err := os.Open(path)
	if err != nil {
		return traceValidationResult{}, fmt.Errorf("ファイルを開けません: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	var records []map[string]any
	lineNum := 0

	for scanner.Scan() {
		lineNum++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		var record map[string]any
		if err := json.Unmarshal([]byte(line), &record); err != nil {
			return traceValidationResult{}, fmt.Errorf("%d行目の JSON 解析に失敗しました: %w", lineNum, err)
		}

		if err := checkSecrets(record); err != nil {
			return traceValidationResult{}, fmt.Errorf("%d行目に秘密情報が含まれています: %w", lineNum, err)
		}

		records = append(records, record)
	}

	if err := scanner.Err(); err != nil {
		return traceValidationResult{}, fmt.Errorf("ファイルの読み込み中にエラーが発生しました: %w", err)
	}

	if len(records) < 2 {
		return traceValidationResult{}, fmt.Errorf("トレースには少なくとも run と result レコードが必要です")
	}

	// 1行目の run レコード検証
	first := records[0]
	if first["record_type"] != "run" {
		return traceValidationResult{}, fmt.Errorf("1行目のレコードは先頭の run レコードである必要があります")
	}
	adapterType, _ := first["adapter_type"].(string)
	if adapterType == "" {
		return traceValidationResult{}, fmt.Errorf("run レコードに adapter_type が指定されていません")
	}
	supportedAdapters := map[string]bool{"codex": true, "opencode": true, "antigravity": true, "generic": true}
	if !supportedAdapters[adapterType] {
		return traceValidationResult{}, fmt.Errorf("未対応の adapter_type です: %s", adapterType)
	}
	benchmarkID, _ := first["benchmark_id"].(string)
	agentName, _ := first["agent_name"].(string)

	// 末尾の result レコード検証
	last := records[len(records)-1]
	if last["record_type"] != "result" {
		return traceValidationResult{}, fmt.Errorf("末尾のレコードは result レコードである必要があります")
	}
	taskSuccess, _ := last["task_success"].(bool)

	// 中間の event レコード検証
	events := records[1 : len(records)-1]
	if len(events) > maxTraceEvents {
		return traceValidationResult{}, fmt.Errorf("イベント数が上限 (%d) を超えています: %d", maxTraceEvents, len(events))
	}

	for i, ev := range events {
		if ev["record_type"] != "event" {
			return traceValidationResult{}, fmt.Errorf("%d行目は event レコードである必要があります", i+2)
		}
		seqVal, exists := ev["sequence"]
		if !exists {
			return traceValidationResult{}, fmt.Errorf("%d行目の event に sequence がありません", i+2)
		}
		seqFloat, ok := seqVal.(float64)
		if !ok || int(seqFloat) != i {
			return traceValidationResult{}, fmt.Errorf("%d行目の event sequence が不連続です (期待値: %d, 実際: %v)", i+2, i, seqVal)
		}
	}

	return traceValidationResult{
		Status:      "valid",
		AdapterType: adapterType,
		BenchmarkID: benchmarkID,
		AgentName:   agentName,
		EventCount:  len(events),
		TaskSuccess: taskSuccess,
		FilePath:    path,
	}, nil
}
