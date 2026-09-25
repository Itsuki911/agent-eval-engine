package main

import (
	"bytes"
	"strings"
	"testing"
)

// モック画面の描画を確認する
func TestMockupRendersAllScreens(t *testing.T) {
	testCases := []struct {
		name     string
		state    appState
		expected string
	}{
		{"home", appState{screen: homeScreen, noClear: true}, "何をしますか？"},
		{"runs", appState{screen: runsScreen, noClear: true}, "EVALUATION RESULTS"},
		{"detail", appState{screen: detailScreen, noClear: true}, "RUN 3c226216"},
		{"trace", appState{screen: traceScreen, noClear: true, traceIndex: 2}, "SELECTED EVENT"},
		{"compare", appState{screen: compareScreen, noClear: true}, "COMPARE"},
		{"confirm", appState{screen: confirmScreen, noClear: true}, "Default: Cancel"},
		{"error", appState{screen: errorScreen, errorKind: "openrouter", noClear: true}, "HTTP 429"},
		{"new evaluation", appState{screen: newEvalScreen, noClear: true}, "STEP 1 / 3"},
		{"search", appState{screen: searchScreen, noClear: true}, "SEARCH RUNS"},
		{"help", appState{screen: helpScreen, noClear: true}, "用語と操作ガイド"},
	}
	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			var output bytes.Buffer
			if err := render(testCase.state, &output); err != nil {
				t.Fatalf("render returned error: %v", err)
			}
			if !strings.Contains(output.String(), testCase.expected) {
				t.Fatalf("missing mockup value: %s", testCase.expected)
			}
		})
	}
}

// モック選択の境界を確認する
func TestMockupSelectionStaysWithinBounds(t *testing.T) {
	testCases := []struct {
		name       string
		first      appState
		last       appState
		firstIndex func(appState) int
		lastIndex  func(appState) int
	}{
		{
			"home", appState{screen: homeScreen}, appState{screen: homeScreen, homeIndex: 4},
			func(state appState) int { return state.homeIndex }, func(state appState) int { return state.homeIndex },
		},
		{
			"runs", appState{screen: runsScreen}, appState{screen: runsScreen, runIndex: 2},
			func(state appState) int { return state.runIndex }, func(state appState) int { return state.runIndex },
		},
		{
			"trace", appState{screen: traceScreen}, appState{screen: traceScreen, traceIndex: 5},
			func(state appState) int { return state.traceIndex }, func(state appState) int { return state.traceIndex },
		},
		{
			"new evaluation", appState{screen: newEvalScreen}, appState{screen: newEvalScreen, newEvalIndex: 1},
			func(state appState) int { return state.newEvalIndex }, func(state appState) int { return state.newEvalIndex },
		},
		{
			"search", appState{screen: searchScreen}, appState{screen: searchScreen, searchIndex: 2},
			func(state appState) int { return state.searchIndex }, func(state appState) int { return state.searchIndex },
		},
	}
	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			first, _ := nextState(testCase.first, "up")
			last, _ := nextState(testCase.last, "down")
			if testCase.firstIndex(first) != 0 {
				t.Fatalf("selection moved before first: %+v", first)
			}
			if testCase.lastIndex(last) != testCase.lastIndex(testCase.last) {
				t.Fatalf("selection moved after last: %+v", last)
			}
		})
	}
}

// モック操作で外部実行しないことを確認する
func TestMockupLiveSelectionOnlyChangesScreen(t *testing.T) {
	state := appState{screen: confirmScreen, confirmIndex: 1}
	next, done := nextState(state, "enter")
	if done || next.screen != detailScreen {
		t.Fatalf("expected detail screen, got: %s", next.screen)
	}
	var output bytes.Buffer
	if err := render(next, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, forbidden := range []string{"OPENROUTER_API_KEY", "DATABASE_URL", "python"} {
		if strings.Contains(output.String(), forbidden) {
			t.Fatalf("mockup exposed engine setting: %s", forbidden)
		}
	}
}

// モック操作をqで終了する
func TestMockupQuitEndsInteraction(t *testing.T) {
	var output bytes.Buffer
	err := runInteractive(
		appState{screen: homeScreen, noClear: true},
		strings.NewReader("\x1b[B\x1b[B\rq"),
		&output,
	)
	if err != nil {
		t.Fatalf("interactive mockup returned error: %v", err)
	}
	if !strings.Contains(output.String(), "NEW EVALUATION") {
		t.Fatal("interactive mockup did not reach selected screen")
	}
}
