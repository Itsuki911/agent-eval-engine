// Agent EvalのCLI/TUIモックを表示する。
package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"

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

	alternateScreenStart = "\033[?1049h\033[2J\033[H"
	alternateScreenEnd   = "\033[?1049l"
)

// UI状態を保持する
type appState struct {
	screen     screenName
	errorKind  string
	noClear    bool
	homeIndex  int
	runIndex   int
	traceIndex   int
	newEvalIndex int
	searchIndex  int
	detailIndex  int
	confirmIndex int
	errorIndex   int
	width        int
	height       int
	backend      bool
	runs         []backendRun
	detail       *backendDetail
	benchmarks   []backendBenchmark
	comparison   *backendComparison
	progress     []backendProgress
	backendError string
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
	backend := flag.Bool("backend", os.Getenv("AGENT_EVAL_BACKEND") != "0", "Python評価エンジンを使う")
	flag.Parse()

	initialScreen := screenName(*screen)
	if *errorKind != "" {
		initialScreen = errorScreen
	}
	return appState{
		screen:     initialScreen,
		errorKind:  *errorKind,
		noClear:    *noClear,
		traceIndex: 2,
		backend:    *backend,
	}
}

// 画面を標準出力へ描画する
func render(state appState, output io.Writer) error {
	if !state.noClear {
		fmt.Fprint(output, backgroundStyle, "\033[2J\033[H")
	} else {
		fmt.Fprint(output, backgroundStyle)
	}
	var content string
	switch state.screen {
	case homeScreen:
		content = renderHome(state.homeIndex)
	case runsScreen:
		if state.backend {
			content = renderBackendRuns(state)
		} else {
			content = renderRuns(state.runIndex)
		}
	case detailScreen:
		if state.backend {
			content = renderBackendDetail(state)
		} else {
			content = renderDetail(state.detailIndex)
		}
	case traceScreen:
		if state.backend {
			content = renderBackendTrace(state)
		} else {
			content = renderTrace(state.traceIndex)
		}
	case compareScreen:
		if state.backend {
			content = renderBackendCompare(state)
		} else {
			content = renderCompare()
		}
	case confirmScreen:
		if state.backend {
			content = renderBackendConfirm(state)
		} else {
			content = renderConfirm(state.confirmIndex)
		}
	case errorScreen:
		if state.backend && state.backendError != "" {
			content = renderBackendError(state)
		} else {
			content = renderError(state.errorKind, state.errorIndex)
		}
	case newEvalScreen:
		if state.backend {
			content = renderBackendNewEvaluation(state)
		} else {
			content = renderNewEvaluation(state.newEvalIndex)
		}
	case searchScreen:
		content = renderSearch(state.searchIndex)
	case helpScreen:
		content = renderHelp()
	default:
		return fmt.Errorf("unknown screen: %s", state.screen)
	}
	content = strings.ReplaceAll(content, divider, dividerFor(state.width))
	content = wrapContent(content, state.width)
	content = strings.ReplaceAll(content, "\n", "\r\n")
	fmt.Fprint(output, content, resetStyle)
	return nil
}

// 端末幅に応じた区切り線を返す
func dividerFor(width int) string {
	if width <= 0 {
		width = 80
	}
	if width < 24 {
		width = 24
	}
	if width > 80 {
		width = 80
	}
	return strings.Repeat("─", width-2)
}

// ANSI色を保って本文を折り返す
func wrapContent(content string, width int) string {
	if width <= 0 {
		width = 80
	}
	if width < 24 {
		width = 24
	}
	lineWidth := width - 2
	var result strings.Builder
	column := 0
	for index := 0; index < len(content); {
		if content[index] == '\x1b' && index+1 < len(content) && content[index+1] == '[' {
			end := index + 2
			for end < len(content) && content[end] != 'm' {
				end++
			}
			if end < len(content) {
				result.WriteString(content[index : end+1])
				index = end + 1
				continue
			}
		}
		runeValue, size := utf8.DecodeRuneInString(content[index:])
		if runeValue == '\n' {
			result.WriteRune(runeValue)
			column = 0
			index += size
			continue
		}
		runeSize := displayWidth(runeValue)
		if column > 0 && column+runeSize > lineWidth {
			result.WriteByte('\n')
			column = 0
		}
		result.WriteRune(runeValue)
		column += runeSize
		index += size
	}
	return result.String()
}

// 端末上の文字幅を返す
func displayWidth(runeValue rune) int {
	if runeValue >= 0x1100 && (runeValue <= 0x115f || runeValue >= 0x2e80) {
		return 2
	}
	return 1
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
func renderNewEvaluation(selectedIndex int) string {
	options := []struct {
		label string
		detail string
	}{
		{"GEN-TOOL-001", "tool selection / record retrieval (ツール呼出・データ取得評価)"},
		{"GEN-SEC-001", "prompt injection defense (プロンプト防御・安全性評価)"},
	}
	if selectedIndex < 0 || selectedIndex >= len(options) {
		selectedIndex = 0
	}
	rows := make([]string, 0, len(options)*3)
	for index, option := range options {
		rows = append(rows, menuOption(index, selectedIndex, option.label, option.detail), "")
	}
	return strings.Join([]string{
		paint(cyanStyle, "NEW EVALUATION"),
		paint(slateStyle, "1 対象を選ぶ  ───  2 実行方法  ───  3 確認  ───  4 結果"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "STEP 1 / 3   評価対象を選択"),
		"",
		rows[0],
		rows[1],
		rows[2],
		rows[3],
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 次へ     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// 実行履歴検索画面を作成する
func renderSearch(selectedIndex int) string {
	options := []struct {
		label string
		detail string
	}{
		{"最近の実行", "直近24時間の実行履歴を表示"},
		{"失敗した実行", "failed / error の実行だけを表示"},
		{"benchmarkで探す", "GEN-TOOL-001などのIDから検索"},
	}
	if selectedIndex < 0 || selectedIndex >= len(options) {
		selectedIndex = 0
	}
	rows := make([]string, 0, len(options)*3)
	for index, option := range options {
		rows = append(rows, menuOption(index, selectedIndex, option.label, option.detail), "")
	}
	return strings.Join([]string{
		paint(cyanStyle, "SEARCH RUNS"),
		paint(slateStyle, "保存済みの評価実行を探します"),
		paint(cyanStyle, divider),
		rows[0],
		rows[1],
		rows[2],
		rows[3],
		rows[4],
		rows[5],
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

// DB実行一覧を画面用に整える
func renderBackendRuns(state appState) string {
	if len(state.runs) == 0 {
		return strings.Join([]string{
			paint(cyanStyle, "EVALUATION RESULTS"),
			paint(slateStyle, "保存済みの実行はありません。"),
			paint(purpleStyle, "新しい評価を開始するからdry-runを実行してください。"),
			paint(cyanStyle, divider),
			paint(blueStyle, "b 戻る     q 終了"),
		}, "\n") + "\n"
	}
	rows := make([]string, 0, len(state.runs)*3)
	for index, run := range state.runs {
		status := paint(slateStyle, run.Status)
		if run.Status == "completed" || run.Status == "simulated" {
			status = paint(greenStyle, "✓ "+run.Status)
		}
		if run.Status == "failed" {
			status = paint(redStyle, "✕ "+run.Status)
		}
		cost := "料金なし"
		if run.CostUSD != nil {
			cost = fmt.Sprintf("$%.8f", *run.CostUSD)
		}
		line := fmt.Sprintf("  %s  %s", run.Benchmark, status)
		if index == state.runIndex {
			line = selected("> "+run.Benchmark+"  "+run.Status)
		}
		rows = append(rows, line, paint(slateStyle, "    "+run.StartedAt+"  |  "+run.Model+"  |  "+cost), "")
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "EVALUATION RESULTS"),
		paint(slateStyle, fmt.Sprintf("PostgreSQLの実行履歴 (%d件)", len(state.runs))),
		paint(cyanStyle, divider),
	}, append(rows, paint(cyanStyle, divider), paint(blueStyle, "↑↓ 選択     Enter 詳細     t Trace     c 比較     r 更新     b 戻る     q 終了"))...), "\n") + "\n"
}

// DB実行詳細を画面用に整える
func renderBackendDetail(state appState) string {
	if state.detail == nil {
		return renderBackendLoading("実行詳細を読み込んでいます")
	}
	detail := state.detail
	status := detail.Status
	if len(detail.Evaluations) > 0 {
		status = detail.Evaluations[0].Status
	}
	cost := "料金なし"
	if detail.CostUSD != nil {
		cost = fmt.Sprintf("$%.8f", *detail.CostUSD)
	}
	metricLines := make([]string, 0, len(detail.Metrics))
	for _, metric := range detail.Metrics {
		metricLines = append(metricLines, paint(slateStyle, fmt.Sprintf("%s.%s: %.2f %s", metric.Category, metric.Name, metric.Value, metric.Unit)))
	}
	if len(metricLines) == 0 {
		metricLines = append(metricLines, paint(slateStyle, "指標はまだありません。"))
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "RUN DETAIL  |  "+detail.RunID),
		paint(greenStyle, "status: "+status),
		paint(cyanStyle, divider),
		paint(purpleStyle, "BENCHMARK  "+detail.Benchmark),
		paint(purpleStyle, "MODEL      "+detail.Model),
		paint(purpleStyle, "COST       "+cost),
		paint(purpleStyle, fmt.Sprintf("EVENTS     %d", len(detail.Events))),
		paint(cyanStyle, divider),
		paint(purpleStyle, "評価指標"),
	}, append(metricLines, paint(cyanStyle, divider), paint(blueStyle, "t Trace     c 比較     r 更新     b 一覧へ戻る     q 終了"))...), "\n") + "\n"
}

// DBイベントを画面用に整える
func renderBackendTrace(state appState) string {
	events := state.progress
	if state.detail != nil {
		events = make([]backendProgress, len(state.detail.Events))
		for index, event := range state.detail.Events {
			events[index] = backendProgress{Type: "progress", Sequence: event.Sequence, EventType: event.EventType, Status: "saved"}
		}
	}
	if len(events) == 0 {
		return renderBackendLoading("実行イベントを待っています")
	}
	index := state.traceIndex
	if index < 0 || index >= len(events) {
		index = len(events) - 1
	}
	rows := make([]string, 0, len(events))
	for eventIndex, event := range events {
		line := fmt.Sprintf("  %03d  %s  %s", event.Sequence, event.EventType, event.Status)
		if eventIndex == index {
			line = selected("> "+line)
		} else {
			line = paint(slateStyle, line)
		}
		rows = append(rows, line)
	}
	detailLines := []string{paint(slateStyle, "進捗イベントを選択しています。")}
	if state.detail != nil && index < len(state.detail.Events) {
		event := state.detail.Events[index]
		detailLines = []string{
			paint(purpleStyle, fmt.Sprintf("EVENT %03d / %s", event.Sequence, event.EventType)),
			paint(slateStyle, "actor: "+event.Actor),
			paint(slateStyle, "payload: "+formatPayload(event.Payload)),
		}
		if len(event.Error) > 0 {
			detailLines = append(detailLines, paint(redStyle, "error: "+formatPayload(event.Error)))
		}
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "TRACE  |  PostgreSQL events"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "処理の流れ (Timeline)"),
	}, append(rows, "", paint(cyanStyle, "SELECTED EVENT"))...), "\n") + "\n" + strings.Join(append(detailLines,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 移動     r 更新     b 戻る     q 終了"),
	), "\n") + "\n"
}

// backend読込中の画面を返す
func renderBackendLoading(message string) string {
	return strings.Join([]string{
		paint(cyanStyle, "AGENT EVAL"),
		paint(amberStyle, message),
		paint(slateStyle, "DBまたはPython評価エンジンへ接続しています。"),
		paint(cyanStyle, divider),
		paint(blueStyle, "q 終了"),
	}, "\n") + "\n"
}

// backend失敗内容を画面用に整える
func renderBackendError(state appState) string {
	return strings.Join([]string{
		paint(redStyle, "BACKEND ERROR  |  "+state.errorKind),
		paint(cyanStyle, divider),
		paint(redStyle, "Python評価エンジンまたはDBへ接続できませんでした。"),
		paint(slateStyle, state.backendError),
		paint(amberStyle, "r 再試行     b 一覧へ戻る     q 終了"),
	}, "\n") + "\n"
}

// backendのbenchmark候補を表示する
func renderBackendNewEvaluation(state appState) string {
	if len(state.benchmarks) == 0 {
		return renderBackendLoading("benchmark候補を読み込んでいます")
	}
	rows := make([]string, 0, len(state.benchmarks)*2)
	for index, benchmark := range state.benchmarks {
		line := "  " + benchmark.ID + "  " + benchmark.Title
		if index == state.newEvalIndex {
			line = selected("> "+benchmark.ID+"  "+benchmark.Title)
		} else {
			line = paint(backgroundStyle, line)
		}
		rows = append(rows, line, paint(slateStyle, "    "+benchmark.Family+"  |  "+benchmark.Path))
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "NEW EVALUATION"),
		paint(slateStyle, "PostgreSQLへ保存する評価を開始します。"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "STEP 1 / 2   benchmarkを選択"),
	}, append(rows, paint(cyanStyle, divider), paint(blueStyle, "↑↓ 選択     Enter 確認     b 戻る     q 終了"))...), "\n") + "\n"
}

// backend実行確認を画面用に整える
func renderBackendConfirm(state appState) string {
	if len(state.benchmarks) == 0 {
		return renderBackendLoading("benchmark候補を読み込んでいます")
	}
	benchmark := state.benchmarks[state.newEvalIndex]
	options := []string{"Cancel (安全に中止する)", "Run evaluation (現在の設定で実行する)"}
	rows := make([]string, len(options))
	for index, option := range options {
		rows[index] = menuOption(index, state.confirmIndex, option, "Enterで決定")
	}
	return strings.Join([]string{
		paint(cyanStyle, "EVALUATION / CONFIRM"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "BENCHMARK   "+benchmark.ID),
		paint(slateStyle, benchmark.Title),
		paint(amberStyle, "現在の設定を使用します。dry-runなら外部APIは呼びません。"),
		"",
		rows[0],
		rows[1],
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 決定     b 戻る     q 終了"),
	}, "\n") + "\n"
}

// backend比較結果を画面用に整える
func renderBackendCompare(state appState) string {
	if state.comparison == nil {
		if len(state.runs) < 2 {
			return strings.Join([]string{
				paint(cyanStyle, "COMPARE"),
				paint(amberStyle, "比較には保存済み実行が2件以上必要です。"),
				paint(blueStyle, "b 一覧へ戻る     q 終了"),
			}, "\n") + "\n"
		}
		return renderBackendLoading("比較結果を読み込んでいます")
	}
	rows := make([]string, 0, len(state.comparison.Metrics))
	for _, metric := range state.comparison.Metrics {
		left := "-"
		right := "-"
		if metric.Left != nil {
			left = fmt.Sprintf("%.2f", *metric.Left)
		}
		if metric.Right != nil {
			right = fmt.Sprintf("%.2f", *metric.Right)
		}
		rows = append(rows, paint(slateStyle, fmt.Sprintf("%s  |  %s → %s  |  %+.2f", metric.Name, left, right, metric.Difference)))
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "COMPARE  |  "+state.comparison.LeftRunID+" ↔ "+state.comparison.RightRunID),
		paint(cyanStyle, divider),
	}, append(rows, paint(cyanStyle, divider), paint(blueStyle, "b 一覧へ戻る     q 終了"))...), "\n") + "\n"
}

// JSON payloadを短く表示する
func formatPayload(payload map[string]any) string {
	encoded, err := json.Marshal(payload)
	if err != nil {
		return "表示できません"
	}
	text := string(encoded)
	if len(text) > 160 {
		return text[:160] + "..."
	}
	return text
}

// backend画面のデータを更新する
func refreshBackendState(state *appState, client backendClient) {
	contextValue := context.Background()
	if state.screen == runsScreen || state.screen == detailScreen || state.screen == traceScreen || state.screen == compareScreen {
		runs, err := client.listRuns(contextValue)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.runs = runs
		if state.runIndex >= len(state.runs) {
			state.runIndex = max(0, len(state.runs)-1)
		}
	}
	if state.screen == newEvalScreen {
		benchmarks, err := client.listBenchmarks(contextValue)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.benchmarks = benchmarks
		if state.newEvalIndex >= len(state.benchmarks) {
			state.newEvalIndex = max(0, len(state.benchmarks)-1)
		}
	}
	if (state.screen == detailScreen || state.screen == traceScreen) && len(state.runs) > 0 {
		detail, err := client.showRun(contextValue, state.runs[state.runIndex].RunID)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.detail = &detail
		if state.traceIndex >= len(detail.Events) {
			state.traceIndex = max(0, len(detail.Events)-1)
		}
	}
	if state.screen == compareScreen && len(state.runs) >= 2 {
		comparison, err := client.compare(contextValue, state.runs[0].RunID, state.runs[1].RunID)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.comparison = &comparison
	}
}

// backend失敗画面へ遷移する
func setBackendError(state *appState, kind string, err error) {
	state.screen = errorScreen
	state.errorKind = kind
	state.backendError = "安全のため詳細は標準エラーへ出力しました。"
}

// 選択benchmarkを評価実行する
func startBackendRun(state *appState, client backendClient, output io.Writer) {
	if len(state.benchmarks) == 0 {
		setBackendError(state, "bridge", fmt.Errorf("benchmark is not selected"))
		return
	}
	benchmark := state.benchmarks[state.newEvalIndex]
	state.progress = nil
	state.detail = nil
	state.screen = traceScreen
	result, err := client.run(context.Background(), benchmark.Path, func(progress backendProgress) {
		state.progress = append(state.progress, progress)
		state.traceIndex = max(0, len(state.progress)-1)
		_ = render(*state, output)
	})
	if err != nil {
		setBackendError(state, "bridge", err)
		return
	}
	runs, err := client.listRuns(context.Background())
	if err != nil {
		setBackendError(state, "bridge", err)
		return
	}
	state.runs = runs
	for index, run := range runs {
		if run.RunID == result.RunID {
			state.runIndex = index
			break
		}
	}
	detail, err := client.showRun(context.Background(), result.RunID)
	if err != nil {
		setBackendError(state, "bridge", err)
		return
	}
	state.detail = &detail
	state.traceIndex = max(0, len(detail.Events)-1)
	state.screen = detailScreen
}

// 詳細画面を作成する
func renderDetail(selectedIndex int) string {
	options := []string{"Traceで処理を見る", "実行結果を比較する", "実行一覧へ戻る"}
	if selectedIndex < 0 || selectedIndex >= len(options) {
		selectedIndex = 0
	}
	rows := make([]string, len(options))
	for index, option := range options {
		rows[index] = menuOption(index, selectedIndex, option, "Enterで開く")
	}
	return strings.Join([]string{
		paint(cyanStyle, "SIGNAL CONSOLE  |  RUN 3c226216  /  GEN-TOOL-001"),
		paint(greenStyle, "✓ completed"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "MODEL  openai/gpt-6-luna     COST  $0.00002390     LATENCY  2.07s     EVENTS  8"),
		paint(slateStyle, "TASK SUCCESS  1.00     SAFETY SCORE  1.00     RETRY COUNT  0     TOOL CALLS  0"),
		paint(cyanStyle, divider),
		"Connectivity test successful.",
		"",
		paint(purpleStyle, "次に行う操作を選択"),
		rows[0],
		rows[1],
		rows[2],
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 開く     t Trace     c 比較     b 戻る     q 終了"),
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
func renderConfirm(selectedIndex int) string {
	options := []string{"Cancel (安全に中止する)", "Run live (外部APIで実行する)"}
	if selectedIndex < 0 || selectedIndex >= len(options) {
		selectedIndex = 0
	}
	rows := make([]string, len(options))
	for index, option := range options {
		rows[index] = menuOption(index, selectedIndex, option, "Enterで決定")
	}
	return strings.Join([]string{
		paint(cyanStyle, "SIGNAL CONSOLE  |  LIVE EVALUATION / CONFIRM"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "BENCHMARK   GEN-TOOL-001"),
		paint(purpleStyle, "MODEL       openai/gpt-6-luna"),
		paint(purpleStyle, "COST LIMIT  $1.00 / run"),
		"",
		paint(redStyle, "! External API request and billing may occur."),
		paint(amberStyle, "Default: Cancel  |  モデルと上限を確認してから選択してください。"),
		paint(slateStyle, "※ 外部APIへの通信と課金が発生する可能性があります。内容を確認して続行してください。"),
		"",
		rows[0],
		rows[1],
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 決定     y 実行する     n 中止する     q 終了"),
	}, "\n") + "\n"
}

// エラー画面を作成する
func renderError(kind string, selectedIndex int) string {
	title, cause, action, guide := errorContent(kind)
	options := []string{"実行一覧へ戻る", "もう一度試す"}
	if selectedIndex < 0 || selectedIndex >= len(options) {
		selectedIndex = 0
	}
	rows := make([]string, len(options))
	for index, option := range options {
		rows[index] = menuOption(index, selectedIndex, option, "Enterで実行")
	}
	return strings.Join([]string{
		paint(redStyle, "SIGNAL CONSOLE  |  ERROR / "+title),
		paint(cyanStyle, divider),
		paint(redStyle, "CAUSE   "+cause),
		paint(amberStyle, "ACTION  "+action),
		paint(slateStyle, "GUIDE   "+guide),
		"",
		rows[0],
		rows[1],
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter 決定     b 戻る     r retry     q 終了"),
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
	if key == "r" && state.backend && state.screen != errorScreen {
		return state, false
	}
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
			state.detailIndex = 0
		case newEvalScreen:
			state.screen = confirmScreen
			state.confirmIndex = 0
		case searchScreen:
			state.screen = runsScreen
		case detailScreen:
			switch state.detailIndex {
			case 0:
				state.screen = traceScreen
			case 1:
				state.screen = compareScreen
			default:
				state.screen = runsScreen
			}
		case confirmScreen:
			if state.confirmIndex == 0 {
				state.screen = newEvalScreen
			} else {
				state.screen = detailScreen
			}
		case errorScreen:
			if state.errorIndex == 0 {
				state.screen = runsScreen
			} else {
				state.screen = confirmScreen
				state.confirmIndex = 0
			}
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
		state.detailIndex = 0
	case "t":
		state.screen = traceScreen
		if state.traceIndex < 0 || state.traceIndex > 5 {
			state.traceIndex = 2
		}
	case "c":
		state.screen = compareScreen
	case "r":
		if state.screen == errorScreen {
			state.screen = confirmScreen
			state.confirmIndex = 0
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
			state.confirmIndex = 1
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
		if state.screen == newEvalScreen && state.newEvalIndex > 0 {
			state.newEvalIndex--
		}
		if state.screen == searchScreen && state.searchIndex > 0 {
			state.searchIndex--
		}
		if state.screen == detailScreen && state.detailIndex > 0 {
			state.detailIndex--
		}
		if state.screen == confirmScreen && state.confirmIndex > 0 {
			state.confirmIndex--
		}
		if state.screen == errorScreen && state.errorIndex > 0 {
			state.errorIndex--
		}
	case "down":
		if state.screen == homeScreen && state.homeIndex < 4 {
			state.homeIndex++
		}
		if state.screen == traceScreen && state.traceIndex < traceLimit(state)-1 {
			state.traceIndex++
		}
		if state.screen == runsScreen && state.runIndex < runLimit(state)-1 {
			state.runIndex++
		}
		if state.screen == newEvalScreen && state.newEvalIndex < benchmarkLimit(state)-1 {
			state.newEvalIndex++
		}
		if state.screen == searchScreen && state.searchIndex < 2 {
			state.searchIndex++
		}
		if state.screen == detailScreen && state.detailIndex < 2 {
			state.detailIndex++
		}
		if state.screen == confirmScreen && state.confirmIndex < 1 {
			state.confirmIndex++
		}
		if state.screen == errorScreen && state.errorIndex < 1 {
			state.errorIndex++
		}
	}
	return state, false
}

// 実行一覧の選択上限を返す
func runLimit(state appState) int {
	if state.backend {
		return len(state.runs)
	}
	return 3
}

// Traceの選択上限を返す
func traceLimit(state appState) int {
	if state.backend {
		if state.detail != nil {
			return len(state.detail.Events)
		}
		return len(state.progress)
	}
	return 6
}

// benchmarkの選択上限を返す
func benchmarkLimit(state appState) int {
	if state.backend {
		return len(state.benchmarks)
	}
	return 2
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
	var client *backendClient
	if state.backend {
		value := newBackendClient()
		client = &value
		if err := client.migrate(context.Background()); err != nil {
			setBackendError(&state, "migration", err)
		} else {
			refreshBackendState(&state, *client)
		}
	}
	originalState, err := term.MakeRaw(fileDescriptor)
	if err != nil {
		return err
	}
	defer term.Restore(fileDescriptor, originalState)
	fmt.Fprint(os.Stdout, alternateScreenStart)
	defer fmt.Fprint(os.Stdout, resetStyle, alternateScreenEnd)
	reader := bufio.NewReader(os.Stdin)
	hasRendered := false
	for {
		width, height, sizeErr := term.GetSize(fileDescriptor)
		if sizeErr == nil {
			state.width = width
			state.height = height
		}
		if hasRendered {
			state.noClear = false
		}
		if err := render(state, os.Stdout); err != nil {
			return err
		}
		hasRendered = true
		key, err := readKey(reader)
		if err != nil {
			return err
		}
		var done bool
		startRun := state.backend && state.screen == confirmScreen && state.confirmIndex == 1 && (key == "enter" || key == "y")
		retryBackend := state.backend && state.screen == errorScreen && key == "r"
		state, done = nextState(state, key)
		if done {
			return nil
		}
		if client != nil {
			if retryBackend {
				if err := client.migrate(context.Background()); err != nil {
					setBackendError(&state, "migration", err)
				} else {
					state.screen = homeScreen
					state.backendError = ""
					refreshBackendState(&state, *client)
				}
			} else if startRun {
				startBackendRun(&state, *client, os.Stdout)
			} else {
				refreshBackendState(&state, *client)
			}
		}
	}
}

// プログラムを開始する
func main() {
	state := parseFlags()
	if err := runTerminal(state); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
