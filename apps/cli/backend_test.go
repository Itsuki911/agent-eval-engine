package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// JSON Lines進捗を読み取る
func TestBackendScanProgressReadsStructuredEvents(t *testing.T) {
	done := make(chan string, 1)
	events := make([]backendProgress, 0)
	input := bytes.NewBufferString("{\"type\":\"progress\",\"sequence\":2,\"event_type\":\"llm_call\",\"status\":\"recorded\"}\n")

	go scanProgress(input, func(progress backendProgress) {
		events = append(events, progress)
	}, done)

	if diagnostic := <-done; diagnostic != "" {
		t.Fatalf("unexpected diagnostic: %s", diagnostic)
	}
	if len(events) != 1 || events[0].EventType != "llm_call" || events[0].Sequence != 2 {
		t.Fatalf("unexpected progress: %+v", events)
	}
}

// backend一覧の選択上限を返す
func TestBackendRunLimitUsesLoadedRuns(t *testing.T) {
	state := appState{backend: true, runs: []backendRun{{RunID: "one"}, {RunID: "two"}}}
	if limit := runLimit(state); limit != 2 {
		t.Fatalf("expected loaded run count, got %d", limit)
	}
}

// backend Traceの選択上限を返す
func TestBackendTraceLimitUsesProgressEvents(t *testing.T) {
	state := appState{backend: true, progress: []backendProgress{{}, {}, {}}}
	if limit := traceLimit(state); limit != 3 {
		t.Fatalf("expected progress count, got %d", limit)
	}
}

// DB実行一覧を描画する
func TestBackendRenderRunsUsesDatabaseValues(t *testing.T) {
	cost := 0.0123
	state := appState{
		backend:  true,
		noClear:  true,
		screen:   runsScreen,
		runIndex: 0,
		runs: []backendRun{{
			RunID:     "run-001",
			Benchmark: "GEN-TOOL-001",
			Status:    "simulated",
			Model:     "openai/gpt-6-luna",
			CostUSD:   &cost,
			StartedAt: "2026-09-25T10:00:00+00:00",
		}},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"PostgreSQLの実行履歴 1-1 / 1", "GEN-TOOL-001", "simulated", "$0.01230000"} {
		if !strings.Contains(output.String(), expected) {
			t.Fatalf("missing database value: %s", expected)
		}
	}
}

// DBイベントをTraceへ描画する
func TestBackendRenderTraceUsesPersistedEvent(t *testing.T) {
	state := appState{
		backend:    true,
		noClear:    true,
		screen:     traceScreen,
		traceIndex: 0,
		detail: &backendDetail{Events: []backendEvent{{
			Sequence:  0,
			EventType: "benchmark_loaded",
			Actor:     "engine",
			Payload:   map[string]any{"benchmark_id": "GEN-TOOL-001"},
		}}},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"benchmark_loaded", "GEN-TOOL-001", "actor: engine"} {
		if !strings.Contains(output.String(), expected) {
			t.Fatalf("missing persisted event value: %s", expected)
		}
	}
}

// 選択benchmarkを確認画面へ渡す
func TestBackendConfirmUsesSelectedBenchmark(t *testing.T) {
	state := appState{
		backend:      true,
		noClear:      true,
		screen:       confirmScreen,
		newEvalIndex: 1,
		benchmarks: []backendBenchmark{
			{ID: "GEN-TOOL-001", Title: "最初の評価"},
			{ID: "COD-BUG-001", Title: "選択中の評価"},
		},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "COD-BUG-001") || !strings.Contains(output.String(), "選択中の評価") {
		t.Fatal("selected benchmark was not rendered")
	}
}

// dry-run判定を詳細画面へ表示する
func TestBackendDetailPrefersEvaluationStatus(t *testing.T) {
	state := appState{
		backend: true,
		noClear: true,
		screen:  detailScreen,
		detail: &backendDetail{
			RunID:       "run-001",
			Status:      "completed",
			Evaluations: []backendResult{{Status: "simulated"}},
		},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "status: simulated") {
		t.Fatal("evaluation status was not rendered")
	}
}

// benchmark一覧をページ単位で描画する
func TestBackendNewEvaluationShowsSinglePage(t *testing.T) {
	benchmarks := make([]backendBenchmark, 5)
	for index := range benchmarks {
		benchmarks[index] = backendBenchmark{ID: "GEN-TOOL-00" + string(rune('1'+index)), Title: "候補"}
	}
	state := appState{
		backend:        true,
		noClear:        true,
		screen:         newEvalScreen,
		height:         24,
		benchmarks:     benchmarks,
		benchmarkTotal: 281,
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "候補 1-5 / 281") {
		t.Fatal("benchmark page information was not rendered")
	}
}

// benchmark境界で次ページへ移動する
func TestBackendBenchmarkSelectionMovesToNextPage(t *testing.T) {
	state := appState{
		backend:         true,
		screen:          newEvalScreen,
		height:          24,
		newEvalIndex:    4,
		benchmarks:      make([]backendBenchmark, 5),
		benchmarkTotal:  10,
		benchmarkOffset: 0,
	}
	next, done := nextState(state, "down")
	if done || next.benchmarkOffset != 5 || next.newEvalIndex != 0 {
		t.Fatalf("expected next page, got offset=%d index=%d", next.benchmarkOffset, next.newEvalIndex)
	}
}

// 実行中のTraceに中止案内を表示する
func TestBackendTraceShowsCancelGuideWhileRunning(t *testing.T) {
	state := appState{
		backend:  true,
		noClear:  true,
		screen:   traceScreen,
		running:  true,
		progress: []backendProgress{{Sequence: 1, EventType: "benchmark_loaded"}},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "q で中止できます") {
		t.Fatal("cancel guide was not rendered")
	}
}

// 中止要求中の状態を表示する
func TestBackendTraceShowsCancellationState(t *testing.T) {
	state := appState{
		backend:    true,
		noClear:    true,
		screen:     traceScreen,
		running:    true,
		cancelling: true,
		progress:   []backendProgress{{Sequence: 1, EventType: "benchmark_loaded"}},
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "評価を中止しています") {
		t.Fatal("cancellation state was not rendered")
	}
}

// 非同期キー入力を受け取る
func TestReadKeysReceivesInputAsynchronously(t *testing.T) {
	updates := readKeys(bufio.NewReader(strings.NewReader("q")))
	update := <-updates
	if update.key != "q" || update.err != nil {
		t.Fatalf("unexpected key update: %+v", update)
	}
}

// ページ移動時だけbackendを更新する
func TestNeedsBackendRefreshForPageChange(t *testing.T) {
	before := appState{screen: newEvalScreen, backend: true, benchmarkOffset: 0}
	after := before
	after.benchmarkOffset = 5
	if !needsBackendRefresh(before, after, "down") {
		t.Fatal("page change must refresh backend data")
	}
	if needsBackendRefresh(before, before, "down") {
		t.Fatal("selection inside a page must not refresh backend data")
	}
}

// exportCSVのJSON応答パースを確認する
func TestBackendExportCSVUnmarshalsResponse(t *testing.T) {
	jsonResponse := `{"status":"exported","path":"/path/to/downloads/agent_eval_runs.csv"}`
	var response struct {
		Status string `json:"status"`
		Path   string `json:"path"`
	}
	if err := json.Unmarshal([]byte(jsonResponse), &response); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if response.Path != "/path/to/downloads/agent_eval_runs.csv" {
		t.Fatalf("unexpected path: %s", response.Path)
	}
}

// createBenchmarkのJSON応答パースを確認する
func TestBackendCreateBenchmarkUnmarshalsResponse(t *testing.T) {
	jsonResponse := `{"status":"created","id":"GEN-USER-001","title":"カスタム評価","family":"generic","path":"benchmarks/user/generic/GEN-USER-001.yaml"}`
	var response backendBenchmark
	if err := json.Unmarshal([]byte(jsonResponse), &response); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if response.ID != "GEN-USER-001" || response.Family != "generic" {
		t.Fatalf("unexpected benchmark: %+v", response)
	}
}

// getTemplateのJSON応答パースを確認する
func TestBackendGetTemplateUnmarshalsResponse(t *testing.T) {
	jsonResponse := `{"schema_version":"0.1","id":"COD-USER-001","family":"coding","task":{"prompt":"test"}}`
	var template map[string]any
	if err := json.Unmarshal([]byte(jsonResponse), &template); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if template["family"] != "coding" || template["id"] != "COD-USER-001" {
		t.Fatalf("unexpected template: %+v", template)
	}
}
