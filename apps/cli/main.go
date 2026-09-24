// Agent EvalのCLI/TUIモックを表示する。
package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"golang.org/x/term"
)

type screenName string

const (
	homeScreen    screenName = "home"
	runsScreen    screenName = "runs"
	detailScreen  screenName = "detail"
	traceScreen   screenName = "trace"
	compareScreen screenName = "compare"
	confirmScreen screenName = "confirm"
	errorScreen   screenName = "error"
	newEvalScreen screenName = "new-evaluation"
	searchScreen  screenName = "search"
	helpScreen    screenName = "help"

	backgroundStyle = "\033[38;2;192;202;245;48;2;26;27;38m"
	cyanStyle       = "\033[38;2;125;207;255;48;2;26;27;38m"
	blueStyle       = "\033[38;2;122;162;247;48;2;26;27;38m"
	purpleStyle     = "\033[38;2;187;154;247;48;2;26;27;38m"
	slateStyle      = "\033[38;2;86;95;137;48;2;26;27;38m"
	greenStyle      = "\033[38;2;158;206;106;48;2;26;27;38m"
	redStyle        = "\033[38;2;247;118;142;48;2;26;27;38m"
	amberStyle      = "\033[38;2;224;175;104;48;2;26;27;38m"
	selectedStyle   = "\033[38;2;192;202;245;48;2;35;45;70m"
	resetStyle      = "\033[0m"

	divider = "────────────────────────────────────────────────────────────────────────"
)

// UI状態を保持する
type appState struct {
	screen     screenName
	errorKind  string
	noClear    bool
	homeIndex  int
	runIndex   int
	traceIndex int
}

// 指定色の文字列を返す
func paint(style string, text string) string {
	return style + text + backgroundStyle
}

// 選択行の文字列を返す
func selected(text string) string {
	return selectedStyle + text + backgroundStyle
}

// 起動引数を読み取る
func parseFlags() appState {
	screen := flag.String("screen", "home", "表示する画面")
	errorKind := flag.String("demo-error", "", "migration, bridge, openrouter")
	noClear := flag.Bool("no-clear", false, "画面消去を無効化")
	flag.Parse()

	return appState{
		screen:     screenName(*screen),
		errorKind:  *errorKind,
		noClear:    *noClear,
		traceIndex: 2,
	}
}

// 画面を標準出力へ描画する
func render(state appState, output io.Writer) error {
	if !state.noClear {
		fmt.Fprint(output, backgroundStyle, "\033[2J\033[H")
	} else {
		fmt.Fprint(output, backgroundStyle)
	}
	if state.errorKind != "" {
		state.screen = errorScreen
	}

	var content string
	switch state.screen {
	case homeScreen:
		content = renderHome(state.homeIndex)
	case runsScreen:
		content = renderRuns(state.runIndex)
	case detailScreen:
		content = renderDetail()
	case traceScreen:
		content = renderTrace(state.traceIndex)
	case compareScreen:
		content = renderCompare()
	case confirmScreen:
		content = renderConfirm()
	case errorScreen:
		content = renderError(state.errorKind)
	case newEvalScreen:
		content = renderNewEvaluation()
	case searchScreen:
		content = renderSearch()
	case helpScreen:
		content = renderHelp()
	default:
		return fmt.Errorf("unknown screen: %s", state.screen)
	}
	fmt.Fprint(output, content, resetStyle)
	return nil
}

// 選択式メニュー行を作成する
func menuOption(index int, selectedIndex int, label string, description string) string {
	prefix := "  "
	if index == selectedIndex {
		prefix = "▶ "
	}
	line := prefix + label
	if index == selectedIndex {
		return selected(line) + "\n  " + paint(slateStyle, description)
	}
	return paint(backgroundStyle, line) + "\n  " + paint(slateStyle, description)
}

// 案内式ホーム画面を作成する
func renderHome(selectedIndex int) string {
	options := []struct {
		label       string
		description string
	}{
		{"評価結果を見る", "過去の実行履歴・結果・Traceを確認"},
		{"Agentの動きを見る", "AIが行った処理を時系列で確認"},
		{"新しい評価を開始する", "benchmarkを選び、dry-runから安全に開始"},
		{"保存済みデータを探す", "benchmark・状態・run IDから実行履歴を検索"},
		{"ヘルプ", "操作方法と用語を確認"},
	}
	if selectedIndex < 0 {
		selectedIndex = 0
	}
	if selectedIndex >= len(options) {
		selectedIndex = len(options) - 1
	}
	lines := []string{
		paint(cyanStyle, "AGENT EVAL  |  AI Agent Evaluation Framework"),
		paint(slateStyle, "AI Agentの評価を実行・確認するターミナルツール (Phase 4 Mockup)"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "何をしますか？ (メニュー番号または矢印キーで選択)"),
		"",
	}
	for index, option := range options {
		lines = append(lines, menuOption(index, selectedIndex, option.label, option.description), "")
	}
	lines = append(lines,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     [1-5] 番号選択     Enter 開く     ? ヘルプ     q 終了"),
	)
	return strings.Join(lines, "\n") + "\n"
}

// 評価開始画面を作成する
func renderNewEvaluation() string {
	return strings.Join([]string{
		paint(cyanStyle, "NEW EVALUATION"),
		paint(slateStyle, "1 対象を選ぶ  ───  2 実行方法  ───  3 確認  ───  4 結果"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "STEP 1 / 3   評価対象を選択"),
		"",
		selected("▶ GEN-TOOL-001"),
		paint(slateStyle, "  tool selection / record retrieval (ツール呼出・データ取得評価)"),
		"",
		paint(backgroundStyle, "  GEN-SEC-001"),
		paint(slateStyle, "  prompt injection defense (プロンプト防御・安全性評価)"),
		"",
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 次へ     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// 実行履歴検索画面を作成する
func renderSearch() string {
	return strings.Join([]string{
		paint(cyanStyle, "SEARCH RUNS"),
		paint(slateStyle, "保存済みの評価実行を探します"),
		paint(cyanStyle, divider),
		selected("▶ 最近の実行"),
		paint(slateStyle, "  直近24時間の実行履歴を表示"),
		"",
		paint(backgroundStyle, "  失敗した実行"),
		paint(slateStyle, "  failed / error の実行だけを表示"),
		"",
		paint(backgroundStyle, "  benchmarkで探す"),
		paint(slateStyle, "  GEN-TOOL-001などのIDから検索"),
		"",
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 検索     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// ヘルプ画面を作成する
func renderHelp() string {
	return strings.Join([]string{
		paint(cyanStyle, "HELP  |  用語と操作ガイド"),
		paint(slateStyle, "Agent Evaluation Engineの主要な概念を説明します"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "Trace (実行トレース)"),
		paint(slateStyle, "評価中に記録された処理の順番です。AIがどう考え、どのツールを呼んだかを追跡できます。"),
		"",
		paint(purpleStyle, "Dry-run (模擬実行)"),
		paint(slateStyle, "外部APIを呼ばずにローカルで処理を確認します。料金は一切発生しません。"),
		"",
		paint(purpleStyle, "Live run (実環境実行)"),
		paint(slateStyle, "実際のLLM APIを使う実行です。高精度な評価ができますが料金が発生する場合があります。"),
		"",
		paint(purpleStyle, "Benchmark (評価ベンチマーク)"),
		paint(slateStyle, "AI Agentの能力（ツール使用や安全性など）を測定するための評価テスト問題です。"),
		paint(cyanStyle, divider),
		paint(blueStyle, "b 戻る     q 終了"),
	}, "\n") + "\n"
}

// 一覧画面を作成する
func renderRuns(selectedIndex int) string {
	runs := []struct {
		id        string
		status    string
		statusRaw string
		detail    string
	}{
		{"GEN-TOOL-001", "✓ completed", "completed", "2026-09-24 21:30  |  gpt-6-luna  |  $0.00002  |  2.07s"},
		{"GEN-SEC-001", "✕ failed", "failed", "2026-09-24 20:15  |  gpt-6-luna  |  $0.00000  |  0.84s"},
		{"GEN-TOOL-001", "○ simulated", "simulated", "2026-09-24 19:58  |  API未使用  |  料金なし"},
	}
	if selectedIndex < 0 {
		selectedIndex = 0
	}
	if selectedIndex >= len(runs) {
		selectedIndex = len(runs) - 1
	}

	rows := make([]string, 0, len(runs)*2)
	for index, run := range runs {
		titleText := fmt.Sprintf("%-14s %s", run.id, run.status)
		if index == selectedIndex {
			rows = append(rows, selected("> "+titleText), selected("    "+run.detail))
			continue
		}
		var statusStyled string
		switch run.statusRaw {
		case "completed":
			statusStyled = paint(greenStyle, run.status)
		case "failed":
			statusStyled = paint(redStyle, run.status)
		default:
			statusStyled = paint(cyanStyle, run.status)
		}
		rowLine := fmt.Sprintf("  %-14s %s", run.id, statusStyled)
		rows = append(rows, rowLine, paint(slateStyle, "    "+run.detail))
	}

	return strings.Join([]string{
		paint(cyanStyle, "EVALUATION RESULTS"),
		paint(slateStyle, "最近の実行を確認します (全3件)"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "3件の実行履歴"),
		paint(slateStyle, "  BENCHMARK      STATUS         日時 / モデル / 料金 / 所要時間"),
		rows[0],
		rows[1],
		"",
		rows[2],
		rows[3],
		"",
		rows[4],
		rows[5],
		"",
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 詳細     t Trace     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// 詳細画面を作成する
func renderDetail() string {
	return strings.Join([]string{
		paint(cyanStyle, "SIGNAL CONSOLE  |  RUN 3c226216  /  GEN-TOOL-001"),
		paint(greenStyle, "✓ completed"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "MODEL  openai/gpt-6-luna     COST  $0.00002390     LATENCY  2.07s     EVENTS  8"),
		paint(slateStyle, "TASK SUCCESS  1.00     SAFETY SCORE  1.00     RETRY COUNT  0     TOOL CALLS  0"),
		paint(cyanStyle, divider),
		"Connectivity test successful.",
		paint(cyanStyle, divider),
		paint(blueStyle, "t Trace     c 比較     b 一覧へ戻る     q 終了"),
	}, "\n") + "\n"
}

// 時系列画面を作成する
func renderTrace(selectedIndex int) string {
	events := []string{
		"● 001  Load benchmark",
		"│ 002  Setup environment",
		"◆ 003  LLM call",
		"│ 004  Tool call",
		"● 005  Evaluate",
		"● 006  Persist results",
	}
	if selectedIndex < 0 {
		selectedIndex = 0
	}
	if selectedIndex >= len(events) {
		selectedIndex = len(events) - 1
	}
	rows := make([]string, len(events))
	for index, event := range events {
		if index == selectedIndex {
			rows[index] = selected("> " + event + "   ◀")
			continue
		}
		rows[index] = paint(slateStyle, "  "+event)
	}
	detailTitle, detailBody := traceDetail(selectedIndex)

	return strings.Join([]string{
		paint(cyanStyle, "TRACE  /  RUN 3c226..."),
		paint(greenStyle, "✓ completed") + "     " + paint(purpleStyle, "6 events") + "     " + paint(slateStyle, "2.07s"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "処理の流れ (Timeline)"),
		rows[0],
		rows[1],
		rows[2],
		rows[3],
		rows[4],
		rows[5],
		"",
		paint(cyanStyle, "─────────────── SELECTED EVENT ───────────────"),
		paint(purpleStyle, detailTitle),
		detailBody[0],
		detailBody[1],
		detailBody[2],
		detailBody[3],
		detailBody[4],
		detailBody[5],
		"",
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 移動     p payload確認     f filter     Enter 詳細     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// 選択イベントの詳細を返す
func traceDetail(index int) (string, []string) {
	details := [][]string{
		{
			paint(slateStyle, "dataset: ") + paint(cyanStyle, "GEN-TOOL-001"),
			paint(slateStyle, "schema: ") + "benchmark-0.1",
			paint(slateStyle, "fixture: ") + "tool-selection-v1",
			paint(slateStyle, "status: ") + paint(greenStyle, "loaded"),
			"",
			paint(slateStyle, "ベンチマーク定義の読み込みが完了しました。"),
		},
		{
			paint(slateStyle, "workspace: ") + paint(greenStyle, "ready"),
			paint(slateStyle, "database: ") + paint(greenStyle, "migrated"),
			paint(slateStyle, "dry_run: ") + "false",
			paint(slateStyle, "status: ") + paint(greenStyle, "ready"),
			"",
			paint(slateStyle, "サンドボックス実行環境を初期化しました。"),
		},
		{
			paint(slateStyle, "model: ") + paint(cyanStyle, "openai/gpt-6-luna"),
			paint(slateStyle, "input tokens: ") + "34",
			paint(slateStyle, "output tokens: ") + "41",
			paint(slateStyle, "cost: ") + paint(amberStyle, "$0.00002390"),
			paint(slateStyle, "retry count: ") + paint(amberStyle, "0"),
			paint(purpleStyle, "PROMPT") + paint(slateStyle, ": run tool task  |  ") + paint(greenStyle, "RESPONSE") + paint(slateStyle, ": Connectivity test successful."),
		},
		{
			paint(slateStyle, "tool: ") + paint(cyanStyle, "selected_tool"),
			paint(slateStyle, "arguments: ") + "{record_id: 42}",
			paint(slateStyle, "result: ") + paint(greenStyle, "success"),
			paint(slateStyle, "duration: ") + "1203ms",
			paint(slateStyle, "retry count: ") + paint(amberStyle, "0"),
			paint(slateStyle, "payload: tool output stored"),
		},
		{
			paint(slateStyle, "metrics: ") + "16",
			paint(slateStyle, "task_success: ") + paint(greenStyle, "1.00"),
			paint(slateStyle, "safety_score: ") + paint(greenStyle, "1.00"),
			paint(slateStyle, "latency: ") + "2072ms",
			"",
			paint(greenStyle, "evaluation completed"),
		},
		{
			paint(slateStyle, "run_id: ") + paint(cyanStyle, "3c226216"),
			paint(slateStyle, "events: ") + "6",
			paint(slateStyle, "metrics: ") + "16",
			paint(slateStyle, "evaluation: ") + paint(greenStyle, "completed"),
			"",
			paint(slateStyle, "history can be reconstructed"),
		},
	}
	titles := []string{
		"EVENT 001 / LOAD (ベンチマーク読み込み)",
		"EVENT 002 / SETUP (実行環境準備)",
		"EVENT 003 / LLM CALL (AIモデル推論・呼び出し)",
		"EVENT 004 / TOOL CALL (ツール実行)",
		"EVENT 005 / EVALUATE (評価・スコア計算)",
		"EVENT 006 / PERSIST (実行結果の永続化)",
	}
	return titles[index], details[index]
}

// 比較画面を作成する
func renderCompare() string {
	return strings.Join([]string{
		paint(cyanStyle, "SIGNAL CONSOLE  |  COMPARE  3c226...  ↔  92ad1..."),
		paint(cyanStyle, divider),
		paint(purpleStyle, "METRIC          RUN A          RUN B          DIFFERENCE"),
		paint(redStyle, "task_success    1.00           0.00           -1.00"),
		paint(greenStyle, "cost            $0.00002       $0.00000       -$0.00002"),
		paint(greenStyle, "latency         2.07s          0.84s          -1.23s"),
		paint(amberStyle, "event_count     8              11             +3"),
		"safety_score    1.00           1.00           0.00",
		paint(cyanStyle, divider),
		paint(blueStyle, "b 一覧へ戻る     q 終了"),
	}, "\n") + "\n"
}

// live実行確認画面を作成する
func renderConfirm() string {
	return strings.Join([]string{
		paint(cyanStyle, "SIGNAL CONSOLE  |  LIVE EVALUATION / CONFIRM"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "BENCHMARK   GEN-TOOL-001"),
		paint(purpleStyle, "MODEL       openai/gpt-6-luna"),
		paint(purpleStyle, "COST LIMIT  $1.00 / run"),
		"",
		paint(redStyle, "! External API request and billing may occur."),
		paint(amberStyle, "Default: Cancel  |  Type y only after checking model and cost limit."),
		paint(slateStyle, "※ 外部APIへの通信と課金が発生する可能性があります。内容を確認して続行してください。"),
		paint(cyanStyle, divider),
		paint(blueStyle, "y 実行する(live)     n 中止する(cancel)     q 終了"),
	}, "\n") + "\n"
}

// エラー画面を作成する
func renderError(kind string) string {
	title, cause, action, guide := errorContent(kind)
	return strings.Join([]string{
		paint(redStyle, "SIGNAL CONSOLE  |  ERROR / "+title),
		paint(cyanStyle, divider),
		paint(redStyle, "CAUSE   "+cause),
		paint(amberStyle, "ACTION  "+action),
		paint(slateStyle, "GUIDE   "+guide),
		paint(cyanStyle, divider),
		paint(blueStyle, "b runsへ戻る     r retry     q 終了"),
	}, "\n") + "\n"
}

// エラー表示内容を返す
func errorContent(kind string) (string, string, string, string) {
	switch kind {
	case "migration":
		return "DB migration failed",
			"Database schema is not current.",
			"Check DATABASE_URL and run migrate_database.py.",
			"DBスキーマが最新ではありません。接続情報を確認しマイグレーションを実行してください。"
	case "bridge":
		return "Python bridge failed",
			"Python process returned a non-zero exit code.",
			"Open stderr details and retry after fixing the error.",
			"Pythonサブプロセスが異常終了しました。詳細ログを確認して再試行してください。"
	case "openrouter":
		return "OpenRouter rate limited",
			"Provider returned HTTP 429 after retry.",
			"Wait for Retry-After, then retry or change model.",
			"OpenRouterのAPI利用制限(429)に達しました。時間を置くかモデルを変更してください。"
	default:
		return "Unknown error",
			"The mock did not receive an error category.",
			"Return to runs and inspect the selected run.",
			"未定義のエラーが発生しました。一覧に戻って実行ログを確認してください。"
	}
}

// キー入力で画面を更新する
func nextState(state appState, key string) (appState, bool) {
	if key == "q" {
		return state, true
	}
	state.errorKind = ""
	switch key {
	case "enter":
		switch state.screen {
		case homeScreen:
			switch state.homeIndex {
			case 0:
				state.screen = runsScreen
			case 1:
				state.screen = traceScreen
				state.traceIndex = 2
			case 2:
				state.screen = newEvalScreen
			case 3:
				state.screen = searchScreen
			case 4:
				state.screen = helpScreen
			}
		case runsScreen:
			state.screen = detailScreen
		case newEvalScreen:
			state.screen = confirmScreen
		case searchScreen:
			state.screen = runsScreen
		}
	case "1":
		if state.screen == homeScreen {
			state.homeIndex = 0
			state.screen = runsScreen
		}
	case "2":
		if state.screen == homeScreen {
			state.homeIndex = 1
			state.screen = traceScreen
			state.traceIndex = 2
		}
	case "3":
		if state.screen == homeScreen {
			state.homeIndex = 2
			state.screen = newEvalScreen
		}
	case "4":
		if state.screen == homeScreen {
			state.homeIndex = 3
			state.screen = searchScreen
		}
	case "5":
		if state.screen == homeScreen {
			state.homeIndex = 4
			state.screen = helpScreen
		}
	case "d":
		state.screen = detailScreen
	case "t":
		state.screen = traceScreen
		if state.traceIndex < 0 || state.traceIndex > 5 {
			state.traceIndex = 2
		}
	case "c":
		state.screen = compareScreen
	case "r":
		if state.screen == errorScreen {
			state.screen = runsScreen
		} else {
			state.screen = confirmScreen
		}
	case "e":
		state.screen = errorScreen
		state.errorKind = "openrouter"
	case "b":
		switch state.screen {
		case detailScreen, traceScreen, compareScreen, confirmScreen, errorScreen:
			state.screen = runsScreen
		default:
			state.screen = homeScreen
		}
	case "?":
		state.screen = helpScreen
	case "y":
		if state.screen == confirmScreen {
			state.screen = detailScreen
		}
	case "n":
		if state.screen == confirmScreen {
			state.screen = runsScreen
		}
	case "up":
		if state.screen == homeScreen && state.homeIndex > 0 {
			state.homeIndex--
		}
		if state.screen == traceScreen && state.traceIndex > 0 {
			state.traceIndex--
		}
		if state.screen == runsScreen && state.runIndex > 0 {
			state.runIndex--
		}
	case "down":
		if state.screen == homeScreen && state.homeIndex < 4 {
			state.homeIndex++
		}
		if state.screen == traceScreen && state.traceIndex < 5 {
			state.traceIndex++
		}
		if state.screen == runsScreen && state.runIndex < 2 {
			state.runIndex++
		}
	}
	return state, false
}

// 入力バイト列を操作名へ変換する
func readKey(reader *bufio.Reader) (string, error) {
	first, err := reader.ReadByte()
	if err != nil {
		return "", err
	}
	if first != 27 {
		if first == '\r' || first == '\n' {
			return "enter", nil
		}
		return string(first), nil
	}
	second, err := reader.ReadByte()
	if err != nil {
		return "escape", nil
	}
	third, err := reader.ReadByte()
	if err != nil || second != '[' {
		return "escape", nil
	}
	if third == 'A' {
		return "up", nil
	}
	if third == 'B' {
		return "down", nil
	}
	return "escape", nil
}

// 対話モードを開始する
func runInteractive(state appState, input io.Reader, output io.Writer) error {
	reader := bufio.NewReader(input)
	for {
		if err := render(state, output); err != nil {
			return err
		}
		key, err := readKey(reader)
		if err == io.EOF {
			return nil
		}
		if err != nil {
			return err
		}
		var done bool
		state, done = nextState(state, key)
		if done {
			return nil
		}
	}
}

// raw modeで対話表示する
func runTerminal(state appState) error {
	fileDescriptor := int(os.Stdin.Fd())
	if !term.IsTerminal(fileDescriptor) {
		return runInteractive(state, os.Stdin, os.Stdout)
	}
	originalState, err := term.MakeRaw(fileDescriptor)
	if err != nil {
		return err
	}
	defer term.Restore(fileDescriptor, originalState)
	reader := bufio.NewReader(os.Stdin)
	for {
		if err := render(state, os.Stdout); err != nil {
			return err
		}
		key, err := readKey(reader)
		if err != nil {
			return err
		}
		var done bool
		state, done = nextState(state, key)
		if done {
			return nil
		}
	}
}

// プログラムを開始する
func main() {
	state := parseFlags()
	if flag.NFlag() > 0 {
		state.noClear = true
		if err := render(state, os.Stdout); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		return
	}
	if err := runTerminal(state); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
