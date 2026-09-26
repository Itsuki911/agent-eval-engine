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
	for _, expected := range []string{"何をしますか？", "評価結果を見る", "新しい評価を開始する", "保存済みデータを探す", "自作benchmarkを確認する"} {
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

// CRLFのEnterを1回の操作として読む
func TestReadKeyConsumesCRLFEnter(t *testing.T) {
	reader := bufio.NewReader(strings.NewReader("\r\n\x1b[B"))
	enter, err := readKey(reader)
	if err != nil || enter != "enter" {
		t.Fatalf("expected enter key, got %q, %v", enter, err)
	}
	down, err := readKey(reader)
	if err != nil || down != "down" {
		t.Fatalf("expected down key after enter, got %q, %v", down, err)
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
		{"5", userBenchmarkScreen, 4},
		{"6", helpScreen, 5},
	}
	for _, tc := range testCases {
		state := appState{screen: homeScreen}
		next, done := nextState(state, tc.key)
		if done || next.screen != tc.expectedScreen || next.homeIndex != tc.expectedIndex {
			t.Errorf("key %s failed: got screen %s index %d", tc.key, next.screen, next.homeIndex)
		}
	}
}

// 自作benchmark一覧からYAMLを開く
func TestUserBenchmarkListOpensYAML(t *testing.T) {
	state := appState{
		screen:         userBenchmarkScreen,
		userBenchmarks: []backendBenchmark{{ID: "GEN-DATA-001", Title: "データ確認"}},
	}
	state, done := nextState(state, "enter")
	if done || state.screen != userBenchmarkYAMLScreen || state.userBenchmarkOffset != 0 {
		t.Fatalf("expected YAML screen, got: %#v", state)
	}
}

// 自作benchmarkのYAMLを表示する
func TestRenderUserBenchmarkYAMLShowsRawContent(t *testing.T) {
	state := appState{
		screen:            userBenchmarkYAMLScreen,
		userBenchmarks:    []backendBenchmark{{ID: "GEN-DATA-001"}},
		userBenchmarkYAML: "id: GEN-DATA-001\ntitle: YAML確認\nfamily: generic\n",
		userBenchmarkPath: "/data/datasets/user/generic/GEN-DATA-001.yaml",
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"BENCHMARK YAML", "id: GEN-DATA-001", "title: YAML確認", "/data/datasets/user/generic/GEN-DATA-001.yaml"} {
		if !strings.Contains(output.String(), expected) {
			t.Fatalf("missing YAML value: %s", expected)
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

// Benchmark作成画面の描画を確認する
func TestCreateBenchmarkScreenRendersProperly(t *testing.T) {
	state := appState{
		screen:       createBenchmarkScreen,
		createFamily: "generic",
		createID:     "GEN-USER-001",
		createTitle:  "テスト用評価",
		noClear:      true,
	}
	var output bytes.Buffer
	if err := render(state, &output); err != nil {
		t.Fatalf("render returned error: %v", err)
	}
	for _, expected := range []string{"BENCHMARK CREATOR", "Family (領域)", "GEN-USER-001", "テスト用評価"} {
		if !strings.Contains(output.String(), expected) {
			t.Fatalf("missing expected text in render: %s", expected)
		}
	}
}

// ホームおよび新規評価画面から作成画面へのキー遷移を確認する
func TestCreateBenchmarkKeyTransitions(t *testing.T) {
	// ホームから 'c' で作成画面へ
	fromHome, _ := nextState(appState{screen: homeScreen}, "c")
	if fromHome.screen != createBenchmarkScreen {
		t.Fatalf("expected createBenchmarkScreen from home 'c', got %s", fromHome.screen)
	}

	// 新規評価から 'c' で作成画面へ
	fromNewEval, _ := nextState(appState{screen: newEvalScreen}, "c")
	if fromNewEval.screen != createBenchmarkScreen {
		t.Fatalf("expected createBenchmarkScreen from newEval 'c', got %s", fromNewEval.screen)
	}

	// 作成画面で 'space' を押すと generic <-> coding が切り替わる
	toggled, _ := nextState(appState{screen: createBenchmarkScreen, createField: 0, createFamily: "generic"}, " ")
	if toggled.createFamily != "coding" {
		t.Fatalf("expected coding after space, got %s", toggled.createFamily)
	}
}

// 作成フォームの全項目を描画する
func TestCreateBenchmarkScreenShowsLimitsAndPrompt(t *testing.T) {
	state := appState{
		screen: createBenchmarkScreen, createFamily: "generic", createID: "GEN-FORM-001",
		createTitle: "入力確認", createPrompt: "一行目\n二行目", createMaxSteps: "8", createTimeout: "30", createMaxCost: "0.05",
	}
	output := renderCreateBenchmark(state)
	for _, expected := range []string{"Fixture", "成功条件", "最大ステップ", "制限時間（秒）", "最大料金（USD）", "一行目 ↵ 二行目"} {
		if !strings.Contains(output, expected) {
			t.Fatalf("missing create field: %s", expected)
		}
	}
}

// 作成フォームへ日本語を入力する
func TestCreateBenchmarkAcceptsUnicodeInput(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 2, createInputMode: true}
	state, _ = nextState(state, "評価")
	state, _ = nextState(state, "タイトル")
	state, _ = nextState(state, "enter")
	if state.createTitle != "評価タイトル" || state.createInputMode {
		t.Fatalf("unicode input was not saved: %#v", state)
	}
}

// 指示プロンプトを複数行で入力する
func TestCreateBenchmarkAcceptsMultilinePrompt(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 5, createInputMode: true}
	state, _ = nextState(state, "一行目")
	state, _ = nextState(state, "enter")
	if state.createPrompt != "一行目\n" || state.createInputMode {
		t.Fatalf("prompt enter was not confirmed: %#v", state)
	}
	state.createInputMode = true
	state, _ = nextState(state, "二行目")
	state, _ = nextState(state, "ctrl+s")
	if state.createPrompt != "一行目\n二行目" || state.createInputMode {
		t.Fatalf("multiline prompt was not saved: %#v", state)
	}
}

// プロンプト確定後に矢印で移動する
func TestCreatePromptEnterEnablesArrowNavigation(t *testing.T) {
	state := appState{
		screen:          createBenchmarkScreen,
		createField:     5,
		createInputMode: true,
		createPrompt:    "Pythonを使用して、helloを表示できる",
	}
	state, _ = nextState(state, "enter")
	if state.createInputMode || state.createPrompt != "Pythonを使用して、helloを表示できる\n" {
		t.Fatalf("prompt was not confirmed: %#v", state)
	}
	state, _ = nextState(state, "down")
	if state.createField != 6 {
		t.Fatalf("arrow key did not move to next field: %#v", state)
	}
}

// 作成フォームの上限値をYAML値へ変換する
func TestCreateBenchmarkDataIncludesLimits(t *testing.T) {
	state := appState{
		createFamily: "coding", createID: "COD-FORM-001", createTitle: "上限確認", createCategory: "bug_fix",
		createFixture: "coding/bash-workspace-v1", createPrompt: "修正してください", createSuccess: "verification_command_exit_code",
		createFailure: "modified_forbidden_path", createNetwork: "disabled", createTags: "bash,security", createMetrics: "task_success,test_success",
		createMaxSteps: "40", createTimeout: "300", createMaxCost: "1.25", createStatus: "active",
	}
	data, err := createBenchmarkData(state)
	if err != nil {
		t.Fatalf("createBenchmarkData returned error: %v", err)
	}
	limits := data["limits"].(map[string]any)
	if limits["max_steps"] != 40 || limits["timeout_seconds"] != 300.0 || limits["max_estimated_cost_usd"] != 1.25 {
		t.Fatalf("unexpected limits: %#v", limits)
	}
	if data["status"] != "active" || data["constraints"].(map[string]any)["network"] != "disabled" {
		t.Fatalf("unexpected advanced data: %#v", data)
	}
}

// 不正な上限値を保存前に拒否する
func TestCreateBenchmarkDataRejectsInvalidLimits(t *testing.T) {
	state := appState{createID: "GEN-FORM-001", createTitle: "不正値", createPrompt: "確認", createMaxSteps: "invalid", createTimeout: "60", createMaxCost: "0.1"}
	if _, err := createBenchmarkData(state); err == nil {
		t.Fatal("invalid max steps must be rejected")
	}
}

// 評価一覧でsampleと自作を切り替える
func TestBenchmarkSourceFilterCycles(t *testing.T) {
	state := appState{screen: newEvalScreen, backend: true, benchmarkSource: "all"}
	state, _ = nextState(state, "s")
	if state.benchmarkSource != "sample" {
		t.Fatalf("expected sample source, got %s", state.benchmarkSource)
	}
	state, _ = nextState(state, "s")
	if state.benchmarkSource != "user-created" {
		t.Fatalf("expected user-created source, got %s", state.benchmarkSource)
	}
}

// UTF-8文字を一文字単位で読む
func TestReadKeyReadsUnicodeRune(t *testing.T) {
	reader := bufio.NewReader(strings.NewReader("評価"))
	first, err := readKey(reader)
	if err != nil || first != "評" {
		t.Fatalf("expected first unicode rune, got %q / %v", first, err)
	}
	second, err := readKey(reader)
	if err != nil || second != "価" {
		t.Fatalf("expected second unicode rune, got %q / %v", second, err)
	}
}

// Escキーで入力解除と終了を検証する
func TestCreateBenchmarkEscapeExitsInputMode(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 5, createInputMode: true}
	afterEsc, done := nextState(state, "escape")
	if done || afterEsc.createInputMode {
		t.Fatalf("expected input mode exited after escape: %#v", afterEsc)
	}
	afterQuit, quitDone := nextState(afterEsc, "q")
	if !quitDone {
		t.Fatal("expected quit after exiting input mode")
	}
	_ = afterQuit
}

// TabとShift+Tabの項目移動を検証する
func TestCreateBenchmarkTabAndBacktabNavigate(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 5, createInputMode: true}
	afterTab, _ := nextState(state, "tab")
	if afterTab.createInputMode || afterTab.createField != 6 {
		t.Fatalf("expected createField 6 without inputMode: %#v", afterTab)
	}
	afterBacktab, _ := nextState(afterTab, "backtab")
	if afterBacktab.createField != 5 {
		t.Fatalf("expected createField 5 after backtab: %#v", afterBacktab)
	}
}

// マウスでフォーカスと解除を検証する
func TestCreateBenchmarkMouseClickFocusAndBlur(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 0, createInputMode: false}
	focused, _ := nextState(state, "mouse:click:10:19")
	if focused.createField != 5 || !focused.createInputMode {
		t.Fatalf("expected prompt focused on click: %#v", focused)
	}
	blurred, _ := nextState(focused, "mouse:click:10:4")
	if blurred.createField != 0 || blurred.createInputMode {
		t.Fatalf("expected choice field focused without inputMode: %#v", blurred)
	}
	outside, _ := nextState(focused, "mouse:click:10:1")
	if outside.createInputMode {
		t.Fatal("expected inputMode blurred when clicking outside")
	}
}

// 入力中でもCtrl+Cで終了を検証する
func TestCreateBenchmarkCtrlCTerminates(t *testing.T) {
	state := appState{screen: createBenchmarkScreen, createField: 5, createInputMode: true}
	_, done := nextState(state, "ctrl+c")
	if !done {
		t.Fatal("ctrl+c must terminate application even in input mode")
	}
}

// 入力中の明確なUI表示を検証する
func TestRenderCreateBenchmarkInputModeUI(t *testing.T) {
	activeState := appState{
		screen: createBenchmarkScreen, createField: 5, createInputMode: true,
		createPrompt: "テストプロンプト",
	}
	activeOutput := renderCreateBenchmark(activeState)
	for _, expected := range []string{"[ ✎", "[Enter] 改行して確定", "[Ctrl+N] 改行を続ける", "[Esc] 確定・脱出", "[Tab] 次の項目", "[Ctrl+C] 終了"} {
		if !strings.Contains(activeOutput, expected) {
			t.Fatalf("missing active input UI element: %s", expected)
		}
	}
	normalState := appState{screen: createBenchmarkScreen, createField: 5, createInputMode: false}
	normalOutput := renderCreateBenchmark(normalState)
	if strings.Contains(normalOutput, "[ ✎") {
		t.Fatal("normal UI should not contain active edit marker")
	}
}

// 拡張キーとマウス入力を検証する
func TestReadKeyParsesTabAndEscapeAndMouse(t *testing.T) {
	tabReader := bufio.NewReader(strings.NewReader("\t"))
	k1, err1 := readKey(tabReader)
	if err1 != nil || k1 != "tab" {
		t.Fatalf("expected tab, got %s / %v", k1, err1)
	}

	escReader := bufio.NewReader(strings.NewReader("\x1b"))
	k2, err2 := readKey(escReader)
	if err2 != nil || k2 != "escape" {
		t.Fatalf("expected escape, got %s / %v", k2, err2)
	}

	backtabReader := bufio.NewReader(strings.NewReader("\x1b[Z"))
	k3, err3 := readKey(backtabReader)
	if err3 != nil || k3 != "backtab" {
		t.Fatalf("expected backtab, got %s / %v", k3, err3)
	}

	mouseReader := bufio.NewReader(strings.NewReader("\x1b[<0;15;8M"))
	k4, err4 := readKey(mouseReader)
	if err4 != nil || k4 != "mouse:click:15:8" {
		t.Fatalf("expected mouse:click:15:8, got %s / %v", k4, err4)
	}
}
