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
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"golang.org/x/term"
)

type screenName string

const (
	homeScreen              screenName = "home"
	runsScreen              screenName = "runs"
	detailScreen            screenName = "detail"
	traceScreen             screenName = "trace"
	compareScreen           screenName = "compare"
	confirmScreen           screenName = "confirm"
	errorScreen             screenName = "error"
	newEvalScreen           screenName = "new-evaluation"
	createBenchmarkScreen   screenName = "create-benchmark"
	userBenchmarkScreen     screenName = "user-benchmark-list"
	userBenchmarkYAMLScreen screenName = "user-benchmark-yaml"
	searchScreen            screenName = "search"
	helpScreen              screenName = "help"

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

	benchmarkCacheLimit        = 10000
	cancellationNoticeDuration = 500 * time.Millisecond

	alternateScreenStart = "\033[?1049h\033[?1000h\033[?1006h\033[2J\033[H"
	alternateScreenEnd   = "\033[?1006l\033[?1000l\033[?1049l"
)

// UI状態を保持する
type appState struct {
	screen               screenName
	errorKind            string
	noClear              bool
	homeIndex            int
	runIndex             int
	traceIndex           int
	newEvalIndex         int
	searchIndex          int
	detailIndex          int
	confirmIndex         int
	errorIndex           int
	width                int
	height               int
	backend              bool
	runs                 []backendRun
	runTotal             int
	runOffset            int
	detail               *backendDetail
	benchmarks           []backendBenchmark
	benchmarkCache       []backendBenchmark
	benchmarkCacheLoaded bool
	benchmarkTotal       int
	benchmarkOffset      int
	benchmarkFamily      string
	benchmarkSource      string
	benchmarkQuery       string
	filterInput          bool
	comparison           *backendComparison
	comparisonOffset     int
	progress             []backendProgress
	traceOffset          int
	running              bool
	cancelling           bool
	cancellationFinished bool
	cancelNoticeUntil    time.Time
	backendError         string
	exportMessage        string
	createFamily         string
	createID             string
	createTitle          string
	createCategory       string
	createFixture        string
	createPrompt         string
	createSuccess        string
	createFailure        string
	createNetwork        string
	createTags           string
	createMetrics        string
	createMaxSteps       string
	createTimeout        string
	createMaxCost        string
	createStatus         string
	createField          int
	createError          string
	createInputMode      bool
	userBenchmarks       []backendBenchmark
	userBenchmarkIndex   int
	userBenchmarkYAML    string
	userBenchmarkPath    string
	userBenchmarkOffset  int
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
		screen:          initialScreen,
		errorKind:       *errorKind,
		noClear:         *noClear,
		traceIndex:      2,
		backend:         *backend,
		benchmarkFamily: "all",
		benchmarkSource: "all",
		createFamily:    "generic",
		createID:        "GEN-USER-001",
		createTitle:     "新しいGeneric評価",
		createCategory:  "task_success",
		createFixture:   "generic/data-processing-v1",
		createPrompt:    "モデルへの評価プロンプトを入力してください",
		createSuccess:   "policy_and_final_state_satisfied",
		createFailure:   "forbidden_action_attempted",
		createNetwork:   "disabled",
		createTags:      "user-created",
		createMetrics:   "task_success,step_count,latency,estimated_cost",
		createMaxSteps:  "12",
		createTimeout:   "60",
		createMaxCost:   "0.10",
		createStatus:    "draft",
	}
}

// 端末高に応じたページ件数を返す
func pageSize(state appState) int {
	if state.height <= 0 {
		return 8
	}
	if state.height < 24 {
		return 5
	}
	rows := (state.height - 10) / 3
	if rows > 12 {
		return 12
	}
	return max(rows, 5)
}

// 表示ページの終端を返す
func pageEnd(offset int, size int, total int) int {
	return min(offset+size, total)
}

// ページ番号を表示用に整える
func pageLabel(offset int, count int, total int) string {
	if total == 0 {
		return "0 / 0"
	}
	return fmt.Sprintf("%d-%d / %d", offset+1, offset+count, total)
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
	case createBenchmarkScreen:
		content = renderCreateBenchmark(state)
	case userBenchmarkScreen:
		content = renderUserBenchmarks(state)
	case userBenchmarkYAMLScreen:
		content = renderUserBenchmarkYAML(state)
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
		{"自作benchmarkを確認する", "自分で保存したYAMLを閲覧（評価は実行しません）"},
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
		paint(greenStyle, "  [c] Benchmark作成ボタン ── 入力形式で評価を作成・保存"),
		"",
	}
	for index, option := range options {
		lines = append(lines, menuOption(index, selectedIndex, option.label, option.description), "")
	}
	lines = append(lines,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     [1-6] 番号選択     c 作成     Enter 開く     ? ヘルプ     q 終了"),
	)
	return strings.Join(lines, "\n") + "\n"
}

// 自作benchmark一覧を表示する
func renderUserBenchmarks(state appState) string {
	if len(state.userBenchmarks) == 0 {
		return strings.Join([]string{
			paint(cyanStyle, "MY BENCHMARKS  |  YAML VIEWER"),
			paint(slateStyle, "自分で作成・保存したbenchmarkだけを確認します。評価は実行しません。"),
			paint(cyanStyle, divider),
			paint(amberStyle, "自作benchmarkはまだありません。ホーム画面の c から作成できます。"),
			paint(cyanStyle, divider),
			paint(blueStyle, "r 更新     b 戻る     q 終了"),
		}, "\n") + "\n"
	}
	rows := make([]string, 0, len(state.userBenchmarks)*2)
	for index, benchmark := range state.userBenchmarks {
		rows = append(rows, menuOption(index, state.userBenchmarkIndex, benchmark.ID, benchmark.Title))
		rows = append(rows, paint(slateStyle, "  "+benchmark.Family+"  |  "+benchmark.Status+"  |  "+benchmark.Path), "")
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "MY BENCHMARKS  |  YAML VIEWER"),
		paint(slateStyle, "自分で作成・保存したbenchmarkだけを確認します。評価は実行しません。"),
		paint(purpleStyle, fmt.Sprintf("保存済み %d 件", len(state.userBenchmarks))),
		paint(cyanStyle, divider),
	}, append(rows,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択     Enter YAMLを開く     r 更新     b 戻る     q 終了"),
	)...), "\n") + "\n"
}

// 自作benchmarkのYAMLを表示する
func renderUserBenchmarkYAML(state appState) string {
	lines := strings.Split(strings.TrimSuffix(state.userBenchmarkYAML, "\n"), "\n")
	if state.userBenchmarkYAML == "" {
		lines = []string{"YAMLを読み込めませんでした。"}
	}
	end := pageEnd(state.userBenchmarkOffset, pageSize(state), len(lines))
	rows := make([]string, 0, end-state.userBenchmarkOffset)
	for _, line := range lines[state.userBenchmarkOffset:end] {
		rows = append(rows, paint(slateStyle, line))
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "BENCHMARK YAML  |  "+selectedUserBenchmarkID(state)),
		paint(slateStyle, state.userBenchmarkPath),
		paint(purpleStyle, "行 "+pageLabel(state.userBenchmarkOffset, len(rows), len(lines))),
		paint(cyanStyle, divider),
	}, append(rows,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ スクロール     b 一覧へ戻る     q 終了"),
	)...), "\n") + "\n"
}

// 選択中の自作benchmark IDを返す
func selectedUserBenchmarkID(state appState) string {
	if state.userBenchmarkIndex >= 0 && state.userBenchmarkIndex < len(state.userBenchmarks) {
		return state.userBenchmarks[state.userBenchmarkIndex].ID
	}
	return "UNKNOWN"
}

// 評価開始画面を作成する
func renderNewEvaluation(selectedIndex int) string {
	options := []struct {
		label  string
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
		label  string
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
	total := state.runTotal
	if total == 0 {
		total = len(state.runs)
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
			line = selected("> " + run.Benchmark + "  " + run.Status)
		}
		rows = append(rows, line, paint(slateStyle, "    "+run.StartedAt+"  |  "+run.Model+"  |  "+cost), "")
	}
	headerLines := []string{
		paint(cyanStyle, "EVALUATION RESULTS"),
		paint(slateStyle, "PostgreSQLの実行履歴 "+pageLabel(state.runOffset, len(state.runs), total)),
	}
	if state.exportMessage != "" {
		headerLines = append(headerLines, state.exportMessage)
	}
	headerLines = append(headerLines, paint(cyanStyle, divider))
	return strings.Join(append(headerLines, append(rows, paint(cyanStyle, divider), paint(blueStyle, "↑↓ 選択・ページ移動     Enter 詳細     t Trace     c 比較     e CSV出力     r 更新     b 戻る     q 終了"))...), "\n") + "\n"
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
	headerLines := []string{
		paint(cyanStyle, "RUN DETAIL  |  "+detail.RunID),
		paint(greenStyle, "status: "+status),
	}
	if state.exportMessage != "" {
		headerLines = append(headerLines, state.exportMessage)
	}
	headerLines = append(headerLines,
		paint(cyanStyle, divider),
		paint(purpleStyle, "BENCHMARK  "+detail.Benchmark),
		paint(purpleStyle, "MODEL      "+detail.Model),
		paint(purpleStyle, "COST       "+cost),
		paint(purpleStyle, fmt.Sprintf("EVENTS     %d", detail.EventTotal)),
		paint(cyanStyle, divider),
		paint(purpleStyle, "評価指標"),
	)
	return strings.Join(append(headerLines, append(metricLines, paint(cyanStyle, divider), paint(blueStyle, "t Trace     c 比較     e CSV出力     r 更新     b 一覧へ戻る     q 終了"))...), "\n") + "\n"
}

// DBイベントを画面用に整える
func renderBackendTrace(state appState) string {
	events := state.progress
	total := len(events)
	if state.detail != nil {
		events = make([]backendProgress, len(state.detail.Events))
		for index, event := range state.detail.Events {
			events[index] = backendProgress{Type: "progress", Sequence: event.Sequence, EventType: event.EventType, Status: "saved"}
		}
		total = state.detail.EventTotal
		if total == 0 {
			total = len(events)
		}
	} else {
		start := min(state.traceOffset, len(events))
		end := pageEnd(start, pageSize(state), len(events))
		events = events[start:end]
	}
	if len(events) == 0 {
		return renderBackendLoading("実行イベントを待っています")
	}
	index := state.traceIndex - state.traceOffset
	if index < 0 || index >= len(events) {
		index = 0
	}
	rows := make([]string, 0, len(events))
	for eventIndex, event := range events {
		line := fmt.Sprintf("  %03d  %s  %s", event.Sequence, event.EventType, event.Status)
		if eventIndex == index {
			line = selected("> " + line)
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
	running := ""
	if state.running {
		if state.cancelling {
			running = paint(amberStyle, "評価を中止しています。候補一覧へ戻ります。")
		} else {
			running = paint(amberStyle, "評価を実行中です。b で中止して候補一覧へ戻れます。")
		}
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "TRACE  |  PostgreSQL events"),
		paint(slateStyle, "イベント "+pageLabel(state.traceOffset, len(events), total)),
		running,
		paint(cyanStyle, divider),
		paint(purpleStyle, "処理の流れ (Timeline)"),
	}, append(rows, "", paint(cyanStyle, "SELECTED EVENT"))...), "\n") + "\n" + strings.Join(append(detailLines,
		paint(cyanStyle, divider),
		paint(blueStyle, "↑↓ 選択・ページ移動     r 更新     b 戻る     q 終了"),
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
			line = selected("> " + benchmark.ID + "  " + benchmark.Title)
		} else {
			line = paint(backgroundStyle, line)
		}
		origin := benchmark.Source
		if origin == "" {
			origin = "sample"
		}
		status := benchmark.Status
		if status == "" {
			status = "active"
		}
		rows = append(rows, line, paint(slateStyle, "    "+origin+"  |  "+status+"  |  "+benchmark.Family+"  |  "+benchmark.Path))
	}
	filter := "all"
	if state.benchmarkFamily != "all" {
		filter = state.benchmarkFamily
	}
	source := state.benchmarkSource
	if source == "" {
		source = "all"
	}
	search := state.benchmarkQuery
	if state.filterInput {
		search += "_"
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "NEW EVALUATION"),
		paint(slateStyle, "候補 "+pageLabel(state.benchmarkOffset, len(state.benchmarks), state.benchmarkTotal)+"  family: "+filter+"  source: "+source),
		paint(cyanStyle, divider),
		paint(purpleStyle, "STEP 1 / 2   benchmarkを選択  search: "+search),
	}, append(rows, paint(cyanStyle, divider), paint(blueStyle, "↑↓ 選択・ページ移動     c 新規作成     f family     s sample/自作     / 検索     Enter 確認     b 戻る     q 終了"))...), "\n") + "\n"
}

const createSaveField = 15

// 作成フォームの入力欄を返す
func createFieldValue(state appState, field int) string {
	values := []string{
		state.createFamily,
		state.createID,
		state.createTitle,
		state.createCategory,
		state.createFixture,
		state.createPrompt,
		state.createSuccess,
		state.createFailure,
		state.createNetwork,
		state.createTags,
		state.createMetrics,
		state.createMaxSteps,
		state.createTimeout,
		state.createMaxCost,
		state.createStatus,
	}
	if field < 0 || field >= len(values) {
		return ""
	}
	return values[field]
}

// 作成フォームの入力欄を更新する
func setCreateFieldValue(state *appState, field int, value string) {
	switch field {
	case 1:
		state.createID = value
	case 2:
		state.createTitle = value
	case 5:
		state.createPrompt = value
	case 9:
		state.createTags = value
	case 10:
		state.createMetrics = value
	case 11:
		state.createMaxSteps = value
	case 12:
		state.createTimeout = value
	case 13:
		state.createMaxCost = value
	}
}

// 作成フォームの入力可否を返す
func isCreateTextField(field int) bool {
	return field == 1 || field == 2 || field == 5 || field == 9 || field == 10 || field == 11 || field == 12 || field == 13
}

// 選択肢を次の値へ進める
func nextChoice(values []string, current string) string {
	for index, value := range values {
		if value == current {
			return values[(index+1)%len(values)]
		}
	}
	return values[0]
}

// カンマ区切りの値を分割する
func splitCSV(value string) []string {
	items := make([]string, 0)
	for _, item := range strings.Split(value, ",") {
		trimmed := strings.TrimSpace(item)
		if trimmed != "" {
			items = append(items, trimmed)
		}
	}
	return items
}

// 作成フォームの値を検証する
func validateCreateForm(state appState) error {
	if state.createID == "" || state.createTitle == "" || state.createPrompt == "" {
		return fmt.Errorf("ID、タイトル、指示プロンプトは必須です")
	}
	maxSteps, err := strconv.Atoi(state.createMaxSteps)
	if err != nil || maxSteps < 1 {
		return fmt.Errorf("最大ステップは整数で入力してください")
	}
	timeout, err := strconv.ParseFloat(state.createTimeout, 64)
	if err != nil || timeout <= 0 {
		return fmt.Errorf("制限時間は数値で入力してください")
	}
	maxCost, err := strconv.ParseFloat(state.createMaxCost, 64)
	if err != nil || maxCost < 0 {
		return fmt.Errorf("最大料金は数値で入力してください")
	}
	return nil
}

// 作成フォームを保存形式へ変換する
func createBenchmarkData(state appState) (map[string]any, error) {
	if err := validateCreateForm(state); err != nil {
		return nil, err
	}
	maxSteps, _ := strconv.Atoi(state.createMaxSteps)
	timeout, _ := strconv.ParseFloat(state.createTimeout, 64)
	maxCost, _ := strconv.ParseFloat(state.createMaxCost, 64)
	return map[string]any{
		"schema_version": "0.1",
		"id":             state.createID,
		"title":          state.createTitle,
		"family":         state.createFamily,
		"category":       state.createCategory,
		"tags":           append([]string{state.createFamily}, splitCSV(state.createTags)...),
		"fixture":        state.createFixture,
		"status":         state.createStatus,
		"metadata": map[string]any{
			"task_version":       1,
			"split":              "dev",
			"source":             "user-created",
			"contamination_risk": "unknown",
			"human_review":       "pending",
		},
		"task":        map[string]any{"prompt": state.createPrompt},
		"constraints": map[string]any{"network": state.createNetwork},
		"expected": map[string]any{
			"success_conditions": []map[string]any{{"type": state.createSuccess}},
			"failure_conditions": []map[string]any{{"type": state.createFailure}},
		},
		"evaluation": map[string]any{
			"required_metrics": splitCSV(state.createMetrics),
			"trace":            map[string]bool{"record_observations": true, "record_actions": true, "record_tool_results": true},
		},
		"limits": map[string]any{
			"max_steps":              maxSteps,
			"timeout_seconds":        timeout,
			"max_estimated_cost_usd": maxCost,
		},
	}, nil
}

// benchmark新規作成画面を作成する
func renderCreateBenchmark(state appState) string {
	fields := []struct {
		name  string
		value string
		desc  string
	}{
		{"Family (領域)", state.createFamily, "Spaceで generic / coding を切替"},
		{"Benchmark ID", state.createID, "スキーマ形式: GEN-xxx-001 または COD-xxx-001"},
		{"タイトル", state.createTitle, "評価の目的・タイトル (1文字以上)"},
		{"カテゴリ", state.createCategory, "Spaceで評価分類を切替"},
		{"Fixture", state.createFixture, "Spaceで実行環境を切替"},
		{"指示プロンプト", state.createPrompt, "Agentへの評価プロンプト"},
		{"成功条件", state.createSuccess, "Spaceで判定条件を切替"},
		{"失敗条件", state.createFailure, "Spaceで失敗判定を切替"},
		{"ネットワーク", state.createNetwork, "Spaceで disabled / enabled を切替"},
		{"タグ", state.createTags, "カンマ区切りで入力"},
		{"必須指標", state.createMetrics, "カンマ区切りで入力"},
		{"最大ステップ", state.createMaxSteps, "1以上の整数"},
		{"制限時間（秒）", state.createTimeout, "0より大きい数値"},
		{"最大料金（USD）", state.createMaxCost, "0以上の数値"},
		{"状態", state.createStatus, "Spaceで draft / active を切替"},
		{"保存と評価開始", "ローカルに保存して評価画面へ進む", "Enterでスキーマ検証＆ローカル保存"},
	}

	rows := make([]string, 0, len(fields)*3)
	for index, field := range fields {
		prefix := "  "
		value := strings.ReplaceAll(field.value, "\n", " ↵ ")
		line := fmt.Sprintf("%-16s : %s", field.name, value)
		if index == state.createField {
			if state.createInputMode {
				line = paint(cyanStyle, "▶ ") + selected(fmt.Sprintf("%-16s : [ ✎ %s █ ]", field.name, value))
			} else {
				prefix = "> "
				line = selected(prefix + line)
			}
		} else {
			line = paint(backgroundStyle, prefix+line)
		}
		rows = append(rows, line, paint(slateStyle, "    "+field.desc), "")
	}

	headerLines := []string{
		paint(cyanStyle, "BENCHMARK CREATOR  |  新しい評価データセットを作成"),
		paint(slateStyle, "フォーム入力から YAML の task / expected / evaluation / limits を保存します"),
	}
	if state.createError != "" {
		headerLines = append(headerLines, paint(redStyle, "エラー: "+state.createError))
	}
	headerLines = append(headerLines, paint(cyanStyle, divider))

	guide := "↑↓ 項目選択     Enter 編集/保存     Space 選択値を切替     Ctrl+N 改行     b 戻る     q 終了"
	if state.createInputMode {
		guide = "[Enter] 改行して確定   [Ctrl+N] 改行を続ける   [Esc] 確定・脱出   [Tab] 次の項目   [Ctrl+C] 終了"
	}

	return strings.Join(append(headerLines, append(rows,
		paint(cyanStyle, divider),
		paint(blueStyle, guide),
	)...), "\n") + "\n"
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
	total := state.comparison.Total
	if total == 0 {
		total = len(state.comparison.Metrics)
	}
	return strings.Join(append([]string{
		paint(cyanStyle, "COMPARE  |  "+state.comparison.LeftRunID+" ↔ "+state.comparison.RightRunID),
		paint(slateStyle, "指標 "+pageLabel(state.comparison.Offset, len(state.comparison.Metrics), total)),
		paint(cyanStyle, divider),
	}, append(rows, paint(cyanStyle, divider), paint(blueStyle, "↑↓ ページ移動     b 一覧へ戻る     q 終了"))...), "\n") + "\n"
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
		runs, total, err := client.listRuns(contextValue, pageSize(*state), state.runOffset)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.runs = runs
		state.runTotal = total
		if state.runIndex >= len(state.runs) {
			state.runIndex = max(0, len(state.runs)-1)
		}
	}
	if state.screen == newEvalScreen {
		refreshBenchmarkView(state, client)
		if state.screen == errorScreen {
			return
		}
	}
	if (state.screen == detailScreen || state.screen == traceScreen) && len(state.runs) > 0 {
		detail, err := client.showRun(
			contextValue,
			state.runs[state.runIndex].RunID,
			pageSize(*state),
			state.traceOffset,
		)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.detail = &detail
		if state.traceIndex >= detail.EventTotal {
			state.traceIndex = max(0, detail.EventTotal-1)
		}
	}
	if state.screen == compareScreen && len(state.runs) >= 2 {
		comparison, err := client.compare(
			contextValue,
			state.runs[0].RunID,
			state.runs[1].RunID,
			pageSize(*state),
			state.comparisonOffset,
		)
		if err != nil {
			setBackendError(state, "bridge", err)
			return
		}
		state.comparison = &comparison
	}
}

// benchmark候補を初回だけ取得する
func loadBenchmarkCache(state *appState, client backendClient) error {
	benchmarks, total, err := client.listBenchmarks(
		context.Background(), "all", "", "all", benchmarkCacheLimit, 0,
	)
	if err != nil {
		return err
	}
	if total > len(benchmarks) {
		return fmt.Errorf("benchmark candidates exceed cache limit: %d", total)
	}
	state.benchmarkCache = benchmarks
	state.benchmarkCacheLoaded = true
	return nil
}

// 条件に合う候補ページを作る
func applyBenchmarkFilter(state *appState) {
	matched := make([]backendBenchmark, 0, len(state.benchmarkCache))
	query := strings.ToLower(state.benchmarkQuery)
	for _, benchmark := range state.benchmarkCache {
		if state.benchmarkFamily != "" && state.benchmarkFamily != "all" && benchmark.Family != state.benchmarkFamily {
			continue
		}
		if state.benchmarkSource != "" && state.benchmarkSource != "all" && benchmark.Source != state.benchmarkSource {
			continue
		}
		if query != "" && !strings.Contains(strings.ToLower(benchmark.ID), query) && !strings.Contains(strings.ToLower(benchmark.Title), query) {
			continue
		}
		matched = append(matched, benchmark)
	}
	state.benchmarkTotal = len(matched)
	if state.benchmarkOffset >= state.benchmarkTotal {
		state.benchmarkOffset = max(0, state.benchmarkTotal-pageSize(*state))
	}
	end := pageEnd(state.benchmarkOffset, pageSize(*state), state.benchmarkTotal)
	state.benchmarks = matched[state.benchmarkOffset:end]
	if state.newEvalIndex >= len(state.benchmarks) {
		state.newEvalIndex = max(0, len(state.benchmarks)-1)
	}
}

// 候補一覧をキャッシュから更新する
func refreshBenchmarkView(state *appState, client backendClient) {
	if !state.benchmarkCacheLoaded {
		if err := loadBenchmarkCache(state, client); err != nil {
			setBackendError(state, "bridge", err)
			return
		}
	}
	applyBenchmarkFilter(state)
}

// 自作benchmark一覧を更新する
func refreshUserBenchmarks(state *appState, client backendClient) {
	benchmarks, _, err := client.listBenchmarks(context.Background(), "all", "", "user-created", benchmarkCacheLimit, 0)
	if err != nil {
		setBackendError(state, "bridge", err)
		return
	}
	state.userBenchmarks = benchmarks
	if state.userBenchmarkIndex >= len(state.userBenchmarks) {
		state.userBenchmarkIndex = max(0, len(state.userBenchmarks)-1)
	}
}

// 選択したYAML原文を更新する
func refreshUserBenchmarkYAML(state *appState, client backendClient) {
	if state.userBenchmarkIndex < 0 || state.userBenchmarkIndex >= len(state.userBenchmarks) {
		return
	}
	value, err := client.showUserBenchmark(context.Background(), state.userBenchmarks[state.userBenchmarkIndex].ID)
	if err != nil {
		setBackendError(state, "bridge", err)
		return
	}
	state.userBenchmarkYAML = value.YAML
	state.userBenchmarkPath = value.Path
	state.userBenchmarkOffset = 0
}

// backend失敗画面へ遷移する
func setBackendError(state *appState, kind string, err error) {
	state.screen = errorScreen
	state.errorKind = kind
	state.backendError = "安全のため詳細は標準エラーへ出力しました。"
}

// 評価実行の更新値を表す
type runUpdate struct {
	progress *backendProgress
	result   *backendRunResult
	err      error
}

// 評価実行を別goroutineで開始する
func startBackendRunAsync(ctx context.Context, state *appState, client backendClient) <-chan runUpdate {
	updates := make(chan runUpdate)
	if len(state.benchmarks) == 0 {
		go func() {
			defer close(updates)
			updates <- runUpdate{err: fmt.Errorf("benchmark is not selected")}
		}()
		return updates
	}
	benchmark := state.benchmarks[state.newEvalIndex]
	state.progress = nil
	state.detail = nil
	state.screen = traceScreen
	state.traceIndex = 0
	state.traceOffset = 0
	state.running = true
	state.cancelling = false
	state.cancellationFinished = false
	state.cancelNoticeUntil = time.Time{}
	go func() {
		defer close(updates)
		result, err := client.run(ctx, benchmark.Path, func(progress backendProgress) {
			select {
			case updates <- runUpdate{progress: &progress}:
			case <-ctx.Done():
			}
		})
		if err != nil {
			updates <- runUpdate{err: err}
			return
		}
		updates <- runUpdate{result: &result}
	}()
	return updates
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

// 作成画面のマウス操作を処理する
func handleCreateBenchmarkMouse(state appState, key string) appState {
	parts := strings.Split(key, ":")
	if len(parts) != 4 {
		return state
	}
	y, err := strconv.Atoi(parts[3])
	if err != nil {
		return state
	}
	headerCount := 3
	if state.createError != "" {
		headerCount = 4
	}
	fieldIndex := (y - headerCount - 1) / 3
	if fieldIndex >= 0 && fieldIndex <= createSaveField {
		state.createField = fieldIndex
		if isCreateTextField(fieldIndex) {
			state.createInputMode = true
			state.createError = ""
		} else {
			state.createInputMode = false
		}
	} else {
		state.createInputMode = false
	}
	return state
}

// キー入力で画面を更新する
func nextState(state appState, key string) (appState, bool) {
	if key == "ctrl+c" {
		return state, true
	}
	if state.screen == createBenchmarkScreen && state.createInputMode {
		value := createFieldValue(state, state.createField)
		switch key {
		case "escape":
			state.createInputMode = false
		case "tab":
			state.createInputMode = false
			if state.createField < createSaveField {
				state.createField++
			} else {
				state.createField = 0
			}
		case "backtab":
			state.createInputMode = false
			if state.createField > 0 {
				state.createField--
			} else {
				state.createField = createSaveField
			}
		case "backspace":
			if len(value) > 0 {
				_, size := utf8.DecodeLastRuneInString(value)
				setCreateFieldValue(&state, state.createField, value[:len(value)-size])
			}
		case "ctrl+s":
			state.createInputMode = false
		case "ctrl+n":
			setCreateFieldValue(&state, state.createField, value+"\n")
		case "enter":
			if state.createField == 5 {
				setCreateFieldValue(&state, state.createField, value+"\n")
			}
			state.createInputMode = false
		default:
			if strings.HasPrefix(key, "mouse:click:") {
				state = handleCreateBenchmarkMouse(state, key)
			} else if key != "up" && key != "down" && key != "pageup" && key != "pagedown" {
				setCreateFieldValue(&state, state.createField, value+key)
			}
		}
		return state, false
	}
	if state.screen == createBenchmarkScreen && !state.createInputMode {
		if strings.HasPrefix(key, "mouse:click:") {
			state = handleCreateBenchmarkMouse(state, key)
			return state, false
		}
		if key == "tab" {
			if state.createField < createSaveField {
				state.createField++
			} else {
				state.createField = 0
			}
			return state, false
		}
		if key == "backtab" {
			if state.createField > 0 {
				state.createField--
			} else {
				state.createField = createSaveField
			}
			return state, false
		}
	}
	if key == "q" {
		return state, true
	}
	if state.backend && state.screen == newEvalScreen && state.filterInput {
		switch key {
		case "enter":
			state.filterInput = false
			state.benchmarkOffset = 0
			state.newEvalIndex = 0
		case "backspace":
			if len(state.benchmarkQuery) > 0 {
				_, size := utf8.DecodeLastRuneInString(state.benchmarkQuery)
				state.benchmarkQuery = state.benchmarkQuery[:len(state.benchmarkQuery)-size]
			}
		case "escape":
			state.filterInput = false
		default:
			if key != "up" && key != "down" && key != "pageup" && key != "pagedown" {
				state.benchmarkQuery += key
			}
		}
		return state, false
	}
	if key == "r" && state.backend && state.screen != errorScreen {
		if state.screen == newEvalScreen {
			state.benchmarkCacheLoaded = false
			state.benchmarkCache = nil
		}
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
				state.screen = userBenchmarkScreen
			case 5:
				state.screen = helpScreen
			}
		case userBenchmarkScreen:
			if len(state.userBenchmarks) > 0 {
				state.screen = userBenchmarkYAMLScreen
				state.userBenchmarkOffset = 0
			}
		case runsScreen:
			state.screen = detailScreen
			state.detailIndex = 0
		case newEvalScreen:
			if !state.backend || len(state.benchmarks) > 0 {
				state.screen = confirmScreen
				state.confirmIndex = 0
			}
		case createBenchmarkScreen:
			if isCreateTextField(state.createField) {
				state.createInputMode = true
				state.createError = ""
			}
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
			state.screen = userBenchmarkScreen
		}
	case "6":
		if state.screen == homeScreen {
			state.homeIndex = 5
			state.screen = helpScreen
		}
	case "d":
		state.screen = detailScreen
		state.detailIndex = 0
	case "t":
		state.screen = traceScreen
		if state.backend {
			state.traceIndex = 0
			state.traceOffset = 0
		} else if state.traceIndex < 0 || state.traceIndex > 5 {
			state.traceIndex = 2
		}
	case "c":
		if state.screen == homeScreen || state.screen == newEvalScreen {
			state.screen = createBenchmarkScreen
			state.createError = ""
		} else {
			state.screen = compareScreen
			state.comparisonOffset = 0
		}
	case " ":
		if state.screen == createBenchmarkScreen {
			switch state.createField {
			case 0:
				if state.createFamily == "generic" {
					state.createFamily = "coding"
					state.createID = "COD-USER-001"
					state.createCategory = "bug_fix"
					state.createFixture = "coding/bash-workspace-v1"
					state.createSuccess = "verification_command_exit_code"
					state.createMaxSteps = "40"
					state.createTimeout = "300"
					state.createMaxCost = "1.00"
				} else {
					state.createFamily = "generic"
					state.createID = "GEN-USER-001"
					state.createCategory = "task_success"
					state.createFixture = "generic/data-processing-v1"
					state.createSuccess = "policy_and_final_state_satisfied"
					state.createMaxSteps = "12"
					state.createTimeout = "60"
					state.createMaxCost = "0.10"
				}
			case 3:
				if state.createFamily == "coding" {
					categories := []string{"bug_fix", "code_generation", "test_fix", "refactoring"}
					for i, cat := range categories {
						if cat == state.createCategory {
							state.createCategory = categories[(i+1)%len(categories)]
							break
						}
					}
				} else {
					categories := []string{"task_success", "tool_selection", "tool_execution", "safety", "recovery"}
					for i, cat := range categories {
						if cat == state.createCategory {
							state.createCategory = categories[(i+1)%len(categories)]
							break
						}
					}
				}
			case 4:
				if state.createFamily == "coding" {
					fixtures := []string{"coding/bash-workspace-v1", "coding/python-workspace-v1", "coding/go-workspace-v1", "coding/c-workspace-v1", "coding/powershell-workspace-v1", "coding/typescript-workspace-v1"}
					state.createFixture = nextChoice(fixtures, state.createFixture)
				} else {
					state.createFixture = "generic/data-processing-v1"
				}
			case 6:
				conditions := []string{"policy_and_final_state_satisfied", "verification_command_exit_code", "structured_output_matches"}
				state.createSuccess = nextChoice(conditions, state.createSuccess)
			case 7:
				conditions := []string{"forbidden_action_attempted", "modified_forbidden_path", "verification_command_failed"}
				state.createFailure = nextChoice(conditions, state.createFailure)
			case 8:
				state.createNetwork = nextChoice([]string{"disabled", "enabled"}, state.createNetwork)
			case 14:
				state.createStatus = nextChoice([]string{"draft", "active"}, state.createStatus)
			}
		}
	case "f":
		if state.backend && state.screen == newEvalScreen {
			switch state.benchmarkFamily {
			case "all":
				state.benchmarkFamily = "generic"
			case "generic":
				state.benchmarkFamily = "coding"
			default:
				state.benchmarkFamily = "all"
			}
			state.benchmarkOffset = 0
			state.newEvalIndex = 0
		}
	case "s":
		if state.backend && state.screen == newEvalScreen {
			switch state.benchmarkSource {
			case "all":
				state.benchmarkSource = "sample"
			case "sample":
				state.benchmarkSource = "user-created"
			default:
				state.benchmarkSource = "all"
			}
			state.benchmarkOffset = 0
			state.newEvalIndex = 0
		}
	case "/":
		if state.backend && state.screen == newEvalScreen {
			state.filterInput = true
		}
	case "r":
		if state.screen == errorScreen {
			state.screen = confirmScreen
			state.confirmIndex = 0
		} else {
			state.screen = confirmScreen
		}
	case "e":
		if state.backend && (state.screen == runsScreen || state.screen == detailScreen) {
			// CSVエクスポート処理をrunTerminalで実行するため画面遷移しない
		} else {
			state.screen = errorScreen
			state.errorKind = "openrouter"
		}
	case "b":
		switch state.screen {
		case userBenchmarkYAMLScreen:
			state.screen = userBenchmarkScreen
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
		if state.screen == userBenchmarkScreen && state.userBenchmarkIndex > 0 {
			state.userBenchmarkIndex--
		}
		if state.screen == userBenchmarkYAMLScreen && state.userBenchmarkOffset > 0 {
			state.userBenchmarkOffset = max(0, state.userBenchmarkOffset-pageSize(state))
		}
		if state.screen == createBenchmarkScreen && state.createField > 0 {
			state.createField--
		}
		if state.screen == traceScreen && state.traceIndex > 0 {
			state.traceIndex--
			if state.backend && state.traceIndex < state.traceOffset {
				state.traceOffset = max(0, state.traceOffset-pageSize(state))
			}
		}
		if state.screen == runsScreen {
			if state.runIndex > 0 {
				state.runIndex--
			} else if state.backend && state.runOffset > 0 {
				state.runOffset = max(0, state.runOffset-pageSize(state))
				state.runIndex = pageSize(state) - 1
			}
		}
		if state.screen == newEvalScreen {
			if state.newEvalIndex > 0 {
				state.newEvalIndex--
			} else if state.backend && state.benchmarkOffset > 0 {
				state.benchmarkOffset = max(0, state.benchmarkOffset-pageSize(state))
				state.newEvalIndex = pageSize(state) - 1
			}
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
		if state.backend && state.screen == compareScreen && state.comparisonOffset > 0 {
			state.comparisonOffset = max(0, state.comparisonOffset-pageSize(state))
		}
	case "down":
		if state.screen == homeScreen && state.homeIndex < 5 {
			state.homeIndex++
		}
		if state.screen == userBenchmarkScreen && state.userBenchmarkIndex < len(state.userBenchmarks)-1 {
			state.userBenchmarkIndex++
		}
		if state.screen == userBenchmarkYAMLScreen && state.userBenchmarkOffset+pageSize(state) < len(strings.Split(strings.TrimSuffix(state.userBenchmarkYAML, "\n"), "\n")) {
			state.userBenchmarkOffset += pageSize(state)
		}
		if state.screen == createBenchmarkScreen && state.createField < createSaveField {
			state.createField++
		}
		if state.screen == traceScreen && state.traceIndex < traceLimit(state)-1 {
			state.traceIndex++
			if state.backend && state.traceIndex >= state.traceOffset+pageSize(state) {
				state.traceOffset += pageSize(state)
			}
		}
		if state.screen == runsScreen {
			if state.runIndex < runLimit(state)-1 {
				state.runIndex++
			} else if state.backend && state.runOffset+len(state.runs) < state.runTotal {
				state.runOffset += len(state.runs)
				state.runIndex = 0
			}
		}
		if state.screen == newEvalScreen {
			if state.newEvalIndex < benchmarkLimit(state)-1 {
				state.newEvalIndex++
			} else if state.backend && state.benchmarkOffset+len(state.benchmarks) < state.benchmarkTotal {
				state.benchmarkOffset += len(state.benchmarks)
				state.newEvalIndex = 0
			}
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
		if state.backend && state.screen == compareScreen && state.comparison != nil && state.comparison.Offset+len(state.comparison.Metrics) < state.comparison.Total {
			state.comparisonOffset += len(state.comparison.Metrics)
		}
	case "pageup":
		if state.backend && state.screen == runsScreen {
			state.runOffset = max(0, state.runOffset-pageSize(state))
			state.runIndex = 0
		}
		if state.backend && state.screen == traceScreen {
			state.traceOffset = max(0, state.traceOffset-pageSize(state))
			state.traceIndex = state.traceOffset
		}
		if state.backend && state.screen == newEvalScreen {
			state.benchmarkOffset = max(0, state.benchmarkOffset-pageSize(state))
			state.newEvalIndex = 0
		}
		if state.backend && state.screen == compareScreen {
			state.comparisonOffset = max(0, state.comparisonOffset-pageSize(state))
		}
	case "pagedown":
		if state.backend && state.screen == runsScreen && state.runOffset+len(state.runs) < state.runTotal {
			state.runOffset += len(state.runs)
			state.runIndex = 0
		}
		if state.backend && state.screen == traceScreen && state.traceIndex+1 < traceLimit(state) {
			state.traceOffset += pageSize(state)
			state.traceIndex = state.traceOffset
		}
		if state.backend && state.screen == newEvalScreen && state.benchmarkOffset+len(state.benchmarks) < state.benchmarkTotal {
			state.benchmarkOffset += len(state.benchmarks)
			state.newEvalIndex = 0
		}
		if state.backend && state.screen == compareScreen && state.comparison != nil && state.comparison.Offset+len(state.comparison.Metrics) < state.comparison.Total {
			state.comparisonOffset += len(state.comparison.Metrics)
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
			return state.detail.EventTotal
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

// SGRマウス入力を解析する
func parseSGRMouse(data string) string {
	if len(data) == 0 {
		return "escape"
	}
	last := data[len(data)-1]
	if last != 'M' {
		return "mouse:release"
	}
	body := data[:len(data)-1]
	parts := strings.Split(body, ";")
	if len(parts) < 3 {
		return "escape"
	}
	btn, bErr := strconv.Atoi(parts[0])
	x, xErr := strconv.Atoi(parts[1])
	y, yErr := strconv.Atoi(parts[2])
	if bErr != nil || xErr != nil || yErr != nil {
		return "escape"
	}
	if btn == 0 {
		return fmt.Sprintf("mouse:click:%d:%d", x, y)
	}
	return "escape"
}

// 入力バイト列を操作名へ変換する
func readKey(reader *bufio.Reader) (string, error) {
	first, err := reader.ReadByte()
	if err != nil {
		return "", err
	}
	if first != 27 {
		if first == '\r' {
			if reader.Buffered() > 0 {
				next, _ := reader.Peek(1)
				if len(next) == 1 && next[0] == '\n' {
					_, _ = reader.ReadByte()
				}
			}
			return "enter", nil
		}
		if first == '\n' {
			return "enter", nil
		}
		if first == '\t' || first == 9 {
			return "tab", nil
		}
		if first == 3 {
			return "ctrl+c", nil
		}
		if first == 19 {
			return "ctrl+s", nil
		}
		if first == 14 {
			return "ctrl+n", nil
		}
		if first == 8 || first == 127 {
			return "backspace", nil
		}
		if first >= utf8.RuneSelf {
			size := 2
			if first&0xf0 == 0xe0 {
				size = 3
			} else if first&0xf8 == 0xf0 {
				size = 4
			}
			bytes := []byte{first}
			for index := 1; index < size; index++ {
				next, readErr := reader.ReadByte()
				if readErr != nil {
					return "", readErr
				}
				bytes = append(bytes, next)
			}
			return string(bytes), nil
		}
		return string(first), nil
	}
	if reader.Buffered() == 0 {
		time.Sleep(15 * time.Millisecond)
		if reader.Buffered() == 0 {
			return "escape", nil
		}
	}
	second, err := reader.ReadByte()
	if err != nil {
		return "escape", nil
	}
	third, err := reader.ReadByte()
	if err != nil || second != '[' {
		return "escape", nil
	}
	if third == 'Z' {
		return "backtab", nil
	}
	if third == '<' {
		var mouseBytes []byte
		for {
			nextByte, readErr := reader.ReadByte()
			if readErr != nil {
				break
			}
			mouseBytes = append(mouseBytes, nextByte)
			if nextByte == 'M' || nextByte == 'm' {
				break
			}
		}
		return parseSGRMouse(string(mouseBytes)), nil
	}
	if third == 'A' {
		return "up", nil
	}
	if third == 'B' {
		return "down", nil
	}
	if third == '5' || third == '6' {
		_, _ = reader.ReadByte()
		if third == '5' {
			return "pageup", nil
		}
		return "pagedown", nil
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

type keyUpdate struct {
	key string
	err error
}

// キー入力を非同期に受け取る
func readKeys(reader *bufio.Reader) <-chan keyUpdate {
	updates := make(chan keyUpdate, 1)
	go func() {
		for {
			key, err := readKey(reader)
			updates <- keyUpdate{key: key, err: err}
			if err != nil {
				close(updates)
				return
			}
		}
	}()
	return updates
}

// 画面更新にDB取得が必要か調べる
func needsBackendRefresh(before appState, after appState, key string) bool {
	if after.filterInput {
		return false
	}
	return key == "r" || before.screen != after.screen ||
		before.runOffset != after.runOffset ||
		before.traceOffset != after.traceOffset ||
		before.comparisonOffset != after.comparisonOffset
}

// 候補表示の再計算要否を返す
func needsBenchmarkViewRefresh(before appState, after appState) bool {
	return after.screen == newEvalScreen && (before.screen != after.screen ||
		before.benchmarkOffset != after.benchmarkOffset ||
		before.benchmarkFamily != after.benchmarkFamily ||
		before.benchmarkSource != after.benchmarkSource ||
		before.benchmarkQuery != after.benchmarkQuery)
}

// 中止案内の表示完了を判定する
func cancellationReadyToExit(state appState, now time.Time) bool {
	return state.cancelling && state.cancellationFinished && !now.Before(state.cancelNoticeUntil)
}

// 中止後に候補一覧へ戻す
func returnToBenchmarkList(state *appState) {
	state.running = false
	state.cancelling = false
	state.cancellationFinished = false
	state.cancelNoticeUntil = time.Time{}
	state.progress = nil
	state.detail = nil
	state.traceIndex = 0
	state.traceOffset = 0
	state.screen = newEvalScreen
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
	keys := readKeys(bufio.NewReader(os.Stdin))
	var updates <-chan runUpdate
	var cancelRun context.CancelFunc
	for {
		width, height, sizeErr := term.GetSize(fileDescriptor)
		if sizeErr == nil {
			state.width = width
			state.height = height
		}
		if err := render(state, os.Stdout); err != nil {
			return err
		}
		state.noClear = false
		if cancellationReadyToExit(state, time.Now()) {
			returnToBenchmarkList(&state)
			continue
		}
		var cancellationTimer <-chan time.Time
		if state.cancelling && state.cancellationFinished {
			cancellationTimer = time.After(time.Until(state.cancelNoticeUntil))
		}
		select {
		case input, open := <-keys:
			if !open || input.err != nil {
				return input.err
			}
			if state.running && input.key == "b" && !state.cancelling {
				state.cancelling = true
				state.cancelNoticeUntil = time.Now().Add(cancellationNoticeDuration)
				cancelRun()
				continue
			}
			if state.running {
				continue
			}
			before := state
			startRun := state.backend && state.screen == confirmScreen && state.confirmIndex == 1 && (input.key == "enter" || input.key == "y")
			retryBackend := state.backend && state.screen == errorScreen && input.key == "r"
			var done bool
			state, done = nextState(state, input.key)
			if done {
				return nil
			}
			if client == nil {
				continue
			}
			if retryBackend {
				if err := client.migrate(context.Background()); err != nil {
					setBackendError(&state, "migration", err)
				} else {
					state.screen = homeScreen
					state.backendError = ""
					refreshBackendState(&state, *client)
				}
			} else if startRun {
				contextValue, cancel := context.WithCancel(context.Background())
				cancelRun = cancel
				updates = startBackendRunAsync(contextValue, &state, *client)
			} else if state.backend && (before.screen == runsScreen || before.screen == detailScreen) && input.key == "e" {
				var targetRunID string
				if before.screen == detailScreen && state.detail != nil {
					targetRunID = state.detail.RunID
				}
				path, err := client.exportCSV(context.Background(), targetRunID)
				if err != nil {
					state.exportMessage = paint(redStyle, "CSVエクスポートに失敗しました: "+err.Error())
				} else {
					state.exportMessage = paint(greenStyle, "✓ CSV保存完了: "+path)
				}
			} else if state.backend && before.screen == createBenchmarkScreen && before.createField == createSaveField && input.key == "enter" {
				data, formErr := createBenchmarkData(before)
				if formErr != nil {
					state.createError = formErr.Error()
				} else {
					created, err := client.createBenchmark(context.Background(), data)
					if err != nil {
						state.createError = err.Error()
					} else {
						state.createError = ""
						if state.benchmarkCacheLoaded {
							state.benchmarkCache = append(state.benchmarkCache, created)
						}
						state.benchmarks = []backendBenchmark{created}
						state.newEvalIndex = 0
						state.confirmIndex = 1
						state.screen = confirmScreen
					}
				}
			} else if state.backend && state.screen == userBenchmarkScreen &&
				(before.screen != userBenchmarkScreen || input.key == "r") {
				refreshUserBenchmarks(&state, *client)
			} else if state.backend && before.screen == userBenchmarkScreen && state.screen == userBenchmarkYAMLScreen {
				refreshUserBenchmarkYAML(&state, *client)
			} else if needsBenchmarkViewRefresh(before, state) ||
				(state.backend && state.screen == newEvalScreen && input.key == "r") {
				refreshBenchmarkView(&state, *client)
			} else if needsBackendRefresh(before, state, input.key) {
				refreshBackendState(&state, *client)
			}
		case <-cancellationTimer:
			returnToBenchmarkList(&state)
		case update, open := <-updates:
			if !open {
				updates = nil
				if state.cancelling {
					state.cancellationFinished = true
				}
				continue
			}
			if update.progress != nil {
				if !state.cancelling {
					state.progress = append(state.progress, *update.progress)
					state.traceIndex = len(state.progress) - 1
					if state.traceIndex >= state.traceOffset+pageSize(state) {
						state.traceOffset = state.traceIndex - pageSize(state) + 1
					}
				}
				continue
			}
			if state.cancelling {
				state.cancellationFinished = true
				continue
			}
			state.running = false
			if update.err != nil {
				setBackendError(&state, "bridge", update.err)
				continue
			}
			if update.result != nil {
				state.runOffset = 0
				state.runIndex = 0
				state.traceOffset = 0
				state.traceIndex = 0
				state.screen = detailScreen
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
