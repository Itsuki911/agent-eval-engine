package main

import (
	"bytes"
	"strings"
	"testing"
)

// ホーム画面の新メニュー8項目をテストする
func TestTUIHomeScreenPhase10Menu(t *testing.T) {
	state := appState{
		screen: homeScreen,
		width:  100,
		height: 30,
	}

	var buf bytes.Buffer
	err := render(state, &buf)
	if err != nil {
		t.Fatalf("render home failed: %v", err)
	}

	output := buf.String()
	expectedItems := []string{
		"新しい評価を開始",
		"評価結果を見る",
		"時系列 Trace を見る",
		"Real Agent 記録を取り込む",
		"Benchmark を管理する",
		"MCP 接続を設定する",
		"設定・診断 (Doctor)",
		"ヘルプ",
	}

	for _, item := range expectedItems {
		if !strings.Contains(output, item) {
			t.Fatalf("home screen missing menu item: %s", item)
		}
	}
}

// 80x24 ターミナルでの表示が崩れないことをテストする
func TestTUISmallTerminalRendering(t *testing.T) {
	screens := []screenName{
		homeScreen,
		wizardScreen,
		importTraceScreen,
		mcpScreen,
		doctorScreen,
		helpScreen,
	}

	for _, s := range screens {
		state := appState{
			screen: s,
			width:  80,
			height: 24,
		}
		var buf bytes.Buffer
		err := render(state, &buf)
		if err != nil {
			t.Fatalf("render %s at 80x24 failed: %v", s, err)
		}
		rendered := buf.String()
		if len(rendered) == 0 {
			t.Fatalf("rendered output for %s was empty", s)
		}
	}
}

// ウィザード画面のステップ遷移をテストする
func TestTUIWizardScreenTransitions(t *testing.T) {
	state := appState{
		screen:      wizardScreen,
		wizardStep:  0,
		wizardTotal: 5,
	}

	// 次へ (Enter または n)
	next, done := nextState(state, "enter")
	if done {
		t.Fatal("wizard should not exit on first enter")
	}
	if next.wizardStep != 1 {
		t.Fatalf("expected step 1, got %d", next.wizardStep)
	}

	// 戻る (b)
	back, _ := nextState(next, "b")
	if back.wizardStep != 0 {
		t.Fatalf("expected step 0, got %d", back.wizardStep)
	}
}
