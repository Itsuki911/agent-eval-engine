package main

import (
	"bytes"
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
	for _, expected := range []string{"PostgreSQLの実行履歴 (1件)", "GEN-TOOL-001", "simulated", "$0.01230000"} {
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
