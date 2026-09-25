package main

import (
	"bufio"
	"bytes"
	"strings"
	"testing"
)

// 一覧画面の主要情報を確認する
func TestRenderRunsShowsRequiredInformation(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: runsScreen, noClear: true}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"EVALUATION RESULTS", "GEN-TOOL-001", "completed", "gpt-6-luna", "$0.00002", "2.07s"} {
		if !strings.Contains(output.String(), expected) {
			t.Errorf("missing column: %s", expected)
		}
	}
}

// ホーム画面の案内項目を確認する
func TestRenderHomeShowsGuidedActions(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: homeScreen, noClear: true}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"何をしますか？", "評価結果を見る", "新しい評価を開始する", "保存済みデータを探す"} {
		if !strings.Contains(output.String(), expected) {
			t.Errorf("missing guided action: %s", expected)
		}
	}
}

// 時系列画面のLLM情報を確認する
func TestRenderTraceShowsTimelineAndLLMDetails(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: traceScreen, noClear: true, traceIndex: 2}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"001", "LLM call", "retry count", "cost", "PROMPT", "RESPONSE"} {
		if !strings.Contains(output.String(), expected) {
			t.Errorf("missing trace value: %s", expected)
		}
	}
}

// 指定配色を画面へ反映する
func TestRenderTraceUsesSelectedPalette(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: traceScreen, noClear: true, traceIndex: 2}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{cyanStyle, blueStyle, purpleStyle, slateStyle, greenStyle, amberStyle} {
		if !strings.Contains(output.String(), expected) {
			t.Error("selected palette color is missing")
		}
	}
}

// 異常画面に失敗色を使う
func TestRenderErrorUsesFailureColor(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: errorScreen, errorKind: "openrouter", noClear: true}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), redStyle) {
		t.Error("failure color is missing")
	}
}

// 異常画面の対処表示を確認する
func TestRenderErrorShowsRecoveryAction(t *testing.T) {
	testCases := []struct {
		kind     string
		expected string
	}{
		{kind: "migration", expected: "migrate_database.py"},
		{kind: "bridge", expected: "stderr details"},
		{kind: "openrouter", expected: "Retry-After"},
	}
	for _, testCase := range testCases {
		t.Run(testCase.kind, func(t *testing.T) {
			var output bytes.Buffer
			err := render(appState{screen: errorScreen, errorKind: testCase.kind, noClear: true}, &output)
			if err != nil {
				t.Fatalf("render returned error: %v", err)
			}
			if !strings.Contains(output.String(), testCase.expected) {
				t.Errorf("missing error guidance: %s", testCase.expected)
			}
		})
	}
}

// 未知画面を拒否する
func TestRenderRejectsUnknownScreen(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: "unknown", noClear: true}, &output)
	if err == nil || !strings.Contains(err.Error(), "unknown screen") {
		t.Fatalf("expected unknown screen error, got: %v", err)
	}
}

// 対話入力でtraceへ遷移する
func TestInteractiveMovesToTraceFromLineInput(t *testing.T) {
	var output bytes.Buffer
	err := runInteractive(
		appState{screen: runsScreen, noClear: true},
		strings.NewReader("t\nq\n"),
		&output,
	)
	if err != nil {
		t.Fatalf("interactive mode returned error: %v", err)
	}
	if !strings.Contains(output.String(), "TRACE  /  RUN 3c226") {
		t.Error("trace screen was not rendered")
	}
	if strings.Contains(output.String(), "Run: 3c226216") {
		t.Error("line ending changed the screen unexpectedly")
	}
}

// 矢印キーでTrace選択を移動する
func TestArrowKeysMoveTraceSelection(t *testing.T) {
	state := appState{screen: traceScreen, traceIndex: 2}
	state, done := nextState(state, "up")
	if done || state.traceIndex != 1 {
		t.Fatalf("up key did not select previous event: %d", state.traceIndex)
	}
	state, done = nextState(state, "down")
	if done || state.traceIndex != 2 {
		t.Fatalf("down key did not select next event: %d", state.traceIndex)
	}
	state.traceIndex = 0
	state, _ = nextState(state, "up")
	if state.traceIndex != 0 {
		t.Fatal("up key moved before first event")
	}
	state.traceIndex = 5
	state, _ = nextState(state, "down")
	if state.traceIndex != 5 {
		t.Fatal("down key moved after last event")
	}
}

// ホーム画面で選択先を開く
func TestHomeEnterOpensSelectedScreen(t *testing.T) {
	state := appState{screen: homeScreen, homeIndex: 2}
	state, done := nextState(state, "enter")
	if done || state.screen != newEvalScreen {
		t.Fatalf("expected new evaluation screen, got: %s", state.screen)
	}
}

// ANSI矢印キーを操作名へ変換する
func TestReadKeyParsesArrowSequence(t *testing.T) {
	reader := bufio.NewReader(strings.NewReader("\x1b[A\x1b[B"))
	up, err := readKey(reader)
	if err != nil || up != "up" {
		t.Fatalf("expected up key, got %q, %v", up, err)
	}
	down, err := readKey(reader)
	if err != nil || down != "down" {
		t.Fatalf("expected down key, got %q, %v", down, err)
	}
}

// 一覧でEnterを押し詳細へ進む
func TestRunsEnterOpensDetailScreen(t *testing.T) {
	state := appState{screen: runsScreen, runIndex: 0}
	state, done := nextState(state, "enter")
	if done || state.screen != detailScreen {
		t.Fatalf("expected detail screen, got: %s", state.screen)
	}
}

// 数字キーで直接画面を開く
func TestHomeNumberKeysNavigateDirectly(t *testing.T) {
	testCases := []struct {
		key            string
		expectedScreen screenName
		expectedIndex  int
	}{
		{"1", runsScreen, 0},
		{"2", traceScreen, 1},
		{"3", newEvalScreen, 2},
		{"4", searchScreen, 3},
		{"5", helpScreen, 4},
	}
	for _, tc := range testCases {
		state := appState{screen: homeScreen}
		next, done := nextState(state, tc.key)
		if done || next.screen != tc.expectedScreen || next.homeIndex != tc.expectedIndex {
			t.Errorf("key %s failed: got screen %s index %d", tc.key, next.screen, next.homeIndex)
		}
	}
}

// 戻るキーで親画面へ戻る
func TestBackKeyNavigatesToParentScreen(t *testing.T) {
	fromDetail, _ := nextState(appState{screen: detailScreen}, "b")
	if fromDetail.screen != runsScreen {
		t.Errorf("expected runsScreen from detail, got: %s", fromDetail.screen)
	}
	fromTrace, _ := nextState(appState{screen: traceScreen}, "b")
	if fromTrace.screen != runsScreen {
		t.Errorf("expected runsScreen from trace, got: %s", fromTrace.screen)
	}
	fromRuns, _ := nextState(appState{screen: runsScreen}, "b")
	if fromRuns.screen != homeScreen {
		t.Errorf("expected homeScreen from runs, got: %s", fromRuns.screen)
	}
}

// Trace配色の回帰を検証する
func TestRenderTraceAmberPaletteRegression(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: traceScreen, noClear: true, traceIndex: 2}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), amberStyle) {
		t.Fatal("regression: amberStyle is missing in traceScreen")
	}
}

// ヘルプの用語解説を確認する
func TestRenderHelpShowsTerminology(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: helpScreen, noClear: true}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, term := range []string{"Trace", "Dry-run", "Live run", "Benchmark"} {
		if !strings.Contains(output.String(), term) {
			t.Errorf("missing terminology in help: %s", term)
		}
	}
}

// 異常画面の初心者案内を確認する
func TestRenderErrorShowsBeginnerGuidance(t *testing.T) {
	var output bytes.Buffer
	err := render(appState{screen: errorScreen, errorKind: "openrouter", noClear: true}, &output)
	if err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "GUIDE") {
		t.Errorf("missing beginner guide in error screen")
	}
}

// 全画面で矢印選択を確認する
func TestArrowKeysOperateAllSelectionScreens(t *testing.T) {
	testCases := []struct {
		name     string
		state    appState
		expected int
	}{
		{"new evaluation", appState{screen: newEvalScreen}, 1},
		{"search", appState{screen: searchScreen}, 1},
		{"detail", appState{screen: detailScreen}, 1},
		{"confirm", appState{screen: confirmScreen}, 1},
		{"error", appState{screen: errorScreen}, 1},
	}
	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			next, done := nextState(testCase.state, "down")
			if done {
				t.Fatal("arrow key unexpectedly ended the UI")
			}
			indexes := []int{next.newEvalIndex, next.searchIndex, next.detailIndex, next.confirmIndex, next.errorIndex}
			if indexes[0]+indexes[1]+indexes[2]+indexes[3]+indexes[4] != testCase.expected {
				t.Fatalf("arrow key did not update selection: %+v", next)
			}
		})
	}
}

// 選択画面から次画面へ進む
func TestEnterOpensSelectedScreenFromAllMenus(t *testing.T) {
	testCases := []struct {
		name     string
		state    appState
		expected screenName
	}{
		{"new evaluation", appState{screen: newEvalScreen, newEvalIndex: 1}, confirmScreen},
		{"search", appState{screen: searchScreen, searchIndex: 2}, runsScreen},
		{"detail trace", appState{screen: detailScreen, detailIndex: 0}, traceScreen},
		{"detail compare", appState{screen: detailScreen, detailIndex: 1}, compareScreen},
		{"confirm cancel", appState{screen: confirmScreen}, newEvalScreen},
		{"confirm live", appState{screen: confirmScreen, confirmIndex: 1}, detailScreen},
		{"error retry", appState{screen: errorScreen, errorIndex: 1}, confirmScreen},
	}
	for _, testCase := range testCases {
		t.Run(testCase.name, func(t *testing.T) {
			next, done := nextState(testCase.state, "enter")
			if done || next.screen != testCase.expected {
				t.Fatalf("expected %s, got %s", testCase.expected, next.screen)
			}
		})
	}
}

// 狭い端末幅で本文を折り返す
func TestWrapContentFitsNarrowTerminal(t *testing.T) {
	content := "評価エンジンの画面幅に応じて長い説明文を安全に折り返します。"
	wrapped := wrapContent(content, 24)
	for _, line := range strings.Split(wrapped, "\n") {
		width := 0
		for _, runeValue := range line {
			width += displayWidth(runeValue)
		}
		if width > 22 {
			t.Fatalf("line exceeds layout width: %q", line)
		}
	}
}

// 端末幅で区切り線を縮める
func TestDividerForUsesTerminalWidth(t *testing.T) {
	if got := len([]rune(dividerFor(40))); got != 38 {
		t.Fatalf("expected 38 columns, got %d", got)
	}
}

// raw mode向け改行を確認する
func TestRenderUsesCarriageReturnAndLineFeed(t *testing.T) {
	var output bytes.Buffer
	if err := render(appState{screen: homeScreen, noClear: true}, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	if !strings.Contains(output.String(), "\r\n") {
		t.Fatal("render must use CRLF for raw terminal mode")
	}
}

// 代替画面バッファを確認する
func TestAlternateScreenSequencesAreDefined(t *testing.T) {
	if !strings.Contains(alternateScreenStart, "?1049h") {
		t.Fatal("alternate screen start sequence is missing")
	}
	if !strings.Contains(alternateScreenEnd, "?1049l") {
		t.Fatal("alternate screen end sequence is missing")
	}
}
