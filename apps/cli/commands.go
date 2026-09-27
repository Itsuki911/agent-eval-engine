package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

const (
	cliVersion       = "0.10.0"
	cliGitCommit     = "release-v0.10.0"
	dbSchemaVersion  = "20260925_0004"
	dockerEngineComp = "29.x / Compose v2.x"
)

// エラー案内を【原因】【次の操作】【詳細ログ】の3項目で構造化する
func formatUserError(cause, action, logPath string) string {
	var sb strings.Builder
	sb.WriteString("\n------------------------------------------------------------\n")
	sb.WriteString("【エラーが発生しました】\n\n")
	sb.WriteString(fmt.Sprintf("【原因】\n  %s\n\n", cause))
	sb.WriteString(fmt.Sprintf("【次の操作】\n  %s\n\n", action))
	if logPath != "" {
		sb.WriteString(fmt.Sprintf("【詳細ログ】\n  %s\n", logPath))
	} else {
		logRoot := resolveUserDataRoot()
		sb.WriteString(fmt.Sprintf("【詳細ログ】\n  %s\n", filepath.Join(logRoot, "logs", "agent-eval.log")))
	}
	sb.WriteString("------------------------------------------------------------\n")
	return sb.String()
}

// CLI サブコマンドを実行する
func executeCLI(args []string, stdout, stderr io.Writer) error {
	if len(args) == 0 {
		return fmt.Errorf("サブコマンドが指定されていません")
	}

	command := args[0]
	cmdArgs := args[1:]

	// --json フラグの検出
	isJSON := false
	filteredArgs := make([]string, 0, len(cmdArgs))
	for _, a := range cmdArgs {
		if a == "--json" {
			isJSON = true
		} else {
			filteredArgs = append(filteredArgs, a)
		}
	}

	switch command {
	case "version", "--version", "-v":
		info := map[string]any{
			"version":              cliVersion,
			"commit":               cliGitCommit,
			"os":                   runtime.GOOS,
			"arch":                 runtime.GOARCH,
			"schema_version":       dbSchemaVersion,
			"docker_compatibility": dockerEngineComp,
		}
		if isJSON {
			encoder := json.NewEncoder(stdout)
			encoder.SetIndent("", "  ")
			return encoder.Encode(info)
		}
		fmt.Fprintf(stdout, "Agent Eval Engine\n  version:         %s (%s)\n", cliVersion, cliGitCommit)
		fmt.Fprintf(stdout, "  OS/Arch:         %s/%s\n", runtime.GOOS, runtime.GOARCH)
		fmt.Fprintf(stdout, "  DB Schema:       %s\n", dbSchemaVersion)
		fmt.Fprintf(stdout, "  Docker Engine:   %s\n", dockerEngineComp)
		return nil

	case "init":
		dataRoot := resolveUserDataRoot()
		paths, err := ensureUserDataDirectories(dataRoot)
		if err != nil {
			msg := formatUserError(
				fmt.Sprintf("データ保存先の作成に失敗しました: %v", err),
				"ディレクトリの作成権限を確認してください",
				"",
			)
			fmt.Fprint(stderr, msg)
			return err
		}

		fmt.Fprintln(stderr, "初期セットアップを開始しています...")
		fmt.Fprintf(stderr, "✓ データ保存先を準備しました: %s\n", paths.Root)

		// 開発リポジトリパスの自動検出と永続化
		currentDir, _ := filepath.Abs(".")
		if _, err := os.Stat(filepath.Join(currentDir, "docker-compose.yml")); err == nil {
			_ = saveConfiguredRepoRoot(paths.Root, currentDir)
			fmt.Fprintf(stderr, "✓ 開発リポジトリを登録しました: %s\n", currentDir)
		} else if envRoot := os.Getenv("AGENT_EVAL_ROOT"); envRoot != "" {
			_ = saveConfiguredRepoRoot(paths.Root, envRoot)
			fmt.Fprintf(stderr, "✓ 開発リポジトリを登録しました: %s\n", envRoot)
		}

		// DBマイグレーション実行
		client := newBackendClient()
		fmt.Fprintln(stderr, "データベースマイグレーションを適用しています...")
		if merr := client.migrate(context.Background()); merr != nil {
			fmt.Fprintf(stderr, "注: DBマイグレーションはコンテナ起動後に適用されます: %v\n", merr)
		} else {
			fmt.Fprintln(stderr, "✓ データベースの準備が完了しました")
		}

		result := map[string]any{
			"status":    "initialized",
			"data_root": paths.Root,
			"version":   cliVersion,
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(result)
		}
		fmt.Fprintln(stdout, "\n初期セットアップが完了しました！")
		fmt.Fprintln(stdout, "次に `agent-eval doctor` で環境の健全性を確認するか、`agent-eval` で TUI を起動してください。")
		return nil

	case "doctor":
		ctx := context.Background()
		report := runSystemDiagnostics(ctx)
		if isJSON {
			return outputDoctorJSON(report, stdout)
		}
		renderDoctorReport(report, stdout)
		if report.OverallStatus == checkStatusFail {
			return fmt.Errorf("システム診断で重大な不備が検出されました")
		}
		return nil

	case "run":
		if len(filteredArgs) == 0 {
			msg := formatUserError(
				"実行対象の benchmark ID が指定されていません",
				"例: agent-eval run GEN-TOOL-001 または agent-eval run COD-PY-001",
				"",
			)
			fmt.Fprint(stderr, msg)
			return fmt.Errorf("benchmark ID is required")
		}
		benchmarkID := filteredArgs[0]
		client := newBackendClient()

		// 評価実行中の進捗を標準エラーに出力
		onProgress := func(p backendProgress) {
			if !isJSON {
				fmt.Fprintf(stderr, ">> [%s] %s (seq: %d)\n", p.Status, p.EventType, p.Sequence)
			}
		}

		res, err := client.run(context.Background(), benchmarkID, onProgress)
		if err != nil {
			msg := formatUserError(
				fmt.Sprintf("評価の実行に失敗しました: %v", err),
				"agent-eval doctor でDBおよびエンジンの状態を確認してください",
				"",
			)
			fmt.Fprint(stderr, msg)
			return err
		}

		if isJSON {
			return json.NewEncoder(stdout).Encode(res)
		}
		fmt.Fprintln(stdout, "\n------------------------------------------------------------")
		fmt.Fprintf(stdout, "評価実行完了: %s\n", res.BenchmarkID)
		fmt.Fprintf(stdout, "Run ID:     %s\n", res.RunID)
		fmt.Fprintf(stdout, "Status:     %s\n", res.Status)
		fmt.Fprintf(stdout, "Events:     %d\n", res.EventCount)
		if res.CostUSD != nil {
			fmt.Fprintf(stdout, "Cost (USD): $%.4f\n", *res.CostUSD)
		}
		fmt.Fprintln(stdout, "------------------------------------------------------------")
		return nil

	case "list":
		client := newBackendClient()
		runs, total, err := client.listRuns(context.Background(), 20, 0)
		if err != nil {
			return err
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(map[string]any{"runs": runs, "total": total})
		}
		fmt.Fprintf(stdout, "保存済み評価実行一覧 (%d 件中 %d 件):\n", total, len(runs))
		for _, r := range runs {
			fmt.Fprintf(stdout, "  - [%s] %s (ID: %s, %s)\n", r.Status, r.Benchmark, r.RunID, r.StartedAt)
		}
		return nil

	case "show":
		if len(filteredArgs) == 0 {
			return fmt.Errorf("run ID を指定してください (例: agent-eval show <run-id>)")
		}
		runID := filteredArgs[0]
		client := newBackendClient()
		detail, err := client.showRun(context.Background(), runID, 20, 0)
		if err != nil {
			return err
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(detail)
		}
		fmt.Fprintf(stdout, "実行詳細: %s (Benchmark: %s)\n", detail.RunID, detail.Benchmark)
		fmt.Fprintf(stdout, "Status: %s, Events: %d, Provider: %s\n", detail.Status, detail.EventTotal, detail.Provider)
		return nil

	case "trace":
		if len(filteredArgs) == 0 {
			return fmt.Errorf("run ID を指定してください (例: agent-eval trace <run-id>)")
		}
		runID := filteredArgs[0]
		client := newBackendClient()
		detail, err := client.showRun(context.Background(), runID, 100, 0)
		if err != nil {
			return err
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(map[string]any{"run_id": runID, "events": detail.Events, "total": detail.EventTotal})
		}
		fmt.Fprintf(stdout, "時系列イベントトレース: %s (%d 件)\n", runID, len(detail.Events))
		for _, ev := range detail.Events {
			fmt.Fprintf(stdout, "  [%03d] %-15s (actor: %s)\n", ev.Sequence, ev.EventType, ev.Actor)
		}
		return nil

	case "compare":
		if len(filteredArgs) < 2 {
			return fmt.Errorf("比較する2つの run ID を指定してください (例: agent-eval compare <left-run-id> <right-run-id>)")
		}
		left, right := filteredArgs[0], filteredArgs[1]
		client := newBackendClient()
		comp, err := client.compare(context.Background(), left, right, 20, 0)
		if err != nil {
			return err
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(comp)
		}
		fmt.Fprintf(stdout, "実行比較: %s vs %s\n", left, right)
		for _, m := range comp.Metrics {
			leftStr := "N/A"
			if m.Left != nil {
				leftStr = fmt.Sprintf("%.2f", *m.Left)
			}
			rightStr := "N/A"
			if m.Right != nil {
				rightStr = fmt.Sprintf("%.2f", *m.Right)
			}
			fmt.Fprintf(stdout, "  %-32s left: %-8s right: %-8s diff: %+.2f\n", m.Name, leftStr, rightStr, m.Difference)
		}
		return nil

	case "validate-trace":
		if len(filteredArgs) == 0 {
			return fmt.Errorf("検証する JSONL ファイルパスを指定してください (例: agent-eval validate-trace ./trace.jsonl)")
		}
		targetPath := filteredArgs[0]
		result, err := validateTraceFile(targetPath)
		if err != nil {
			msg := formatUserError(
				fmt.Sprintf("トレース検証に失敗しました: %v", err),
				"JSONL ファイルの形式（1行目run, 中間event連番, 末尾result）および秘密情報を含んでいないか確認してください",
				"",
			)
			fmt.Fprint(stderr, msg)
			return err
		}
		if isJSON {
			return json.NewEncoder(stdout).Encode(result)
		}
		fmt.Fprintf(stdout, "✓ トレース検証成功: %s\n", targetPath)
		fmt.Fprintf(stdout, "  Adapter: %s\n", result.AdapterType)
		fmt.Fprintf(stdout, "  Benchmark: %s\n", result.BenchmarkID)
		fmt.Fprintf(stdout, "  Events: %d\n", result.EventCount)
		fmt.Fprintf(stdout, "  Success: %v\n", result.TaskSuccess)
		return nil

	case "import-trace":
		if len(filteredArgs) == 0 {
			return fmt.Errorf("取り込む JSONL ファイルパスを指定してください (例: agent-eval import-trace ./trace.jsonl)")
		}
		targetPath := filteredArgs[0]
		// まず検証
		validation, err := validateTraceFile(targetPath)
		if err != nil {
			msg := formatUserError(
				fmt.Sprintf("取り込み前の形式検証でエラーが発生しました: %v", err),
				"JSONL の形式を修正して再実行してください",
				"",
			)
			fmt.Fprint(stderr, msg)
			return err
		}

		// バックエンドを通じてDBにインポート
		client := newBackendClient()
		outBytes, err := client.execute(context.Background(), []string{"import-trace", "--file", targetPath}, nil)
		if err != nil {
			msg := formatUserError(
				fmt.Sprintf("トレースのデータベース取り込みに失敗しました: %v", err),
				"agent-eval doctor でデータベース接続状態を確認してください",
				"",
			)
			fmt.Fprint(stderr, msg)
			return err
		}

		if isJSON {
			stdout.Write(outBytes)
			return nil
		}

		var importRes struct {
			RunID       string `json:"run_id"`
			Status      string `json:"status"`
			EventCount  int    `json:"event_count"`
			AdapterType string `json:"adapter_type"`
		}
		json.Unmarshal(outBytes, &importRes)

		fmt.Fprintf(stdout, "✓ Real Agent トレースの取り込みが完了しました！\n")
		fmt.Fprintf(stdout, "  Run ID:      %s\n", importRes.RunID)
		fmt.Fprintf(stdout, "  Adapter:     %s\n", validation.AdapterType)
		fmt.Fprintf(stdout, "  Event Count: %d\n", validation.EventCount)
		fmt.Fprintf(stdout, "  Task Status: %s\n\n", importRes.Status)
		fmt.Fprintf(stdout, "時系列イベントを確認するには次を実行してください:\n")
		fmt.Fprintf(stdout, "  agent-eval trace %s\n", importRes.RunID)
		return nil

	case "mcp":
		return runMCPCommand(filteredArgs, stdout, stderr)

	case "help", "--help", "-h":
		printHelp(stdout)
		return nil

	default:
		msg := formatUserError(
			fmt.Sprintf("未知のサブコマンドです: %s", command),
			"使用可能なコマンドを確認するには `agent-eval --help` を実行してください",
			"",
		)
		fmt.Fprint(stderr, msg)
		return fmt.Errorf("unknown subcommand: %s", command)
	}
}

// 利用者向けヘルプを表示する
func printHelp(w io.Writer) {
	fmt.Fprintln(w, "Agent Eval Engine - AI Agent 評価・記録・比較基盤")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "利用方法:")
	fmt.Fprintln(w, "  agent-eval [command] [options]")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "コマンド:")
	fmt.Fprintln(w, "  (引数なし)                 対話型 TUI を起動")
	fmt.Fprintln(w, "  init                       初回セットアップ、データ保存先・DBの準備")
	fmt.Fprintln(w, "  doctor                     Docker、DB、設定、マイグレーション環境の診断")
	fmt.Fprintln(w, "  version                    バージョン情報の表示")
	fmt.Fprintln(w, "  run <benchmark-id>         benchmark を実行して評価")
	fmt.Fprintln(w, "  list                       保存済みの評価実行履歴を一覧表示")
	fmt.Fprintln(w, "  show <run-id>              指定した評価実行の詳細を表示")
	fmt.Fprintln(w, "  trace <run-id>             指定した評価実行の時系列イベントを表示")
	fmt.Fprintln(w, "  compare <left> <right>     2つの評価実行結果・指標を比較")
	fmt.Fprintln(w, "  validate-trace <file>      外部 Agent 記録 (JSONL) の形式を安全に検証")
	fmt.Fprintln(w, "  import-trace <file>        外部 Agent 記録 (JSONL) を評価 DB へ取り込み")
	fmt.Fprintln(w, "  mcp install codex          Codex 向け MCP Server 登録案内")
	fmt.Fprintln(w, "  mcp serve --stdio          MCP Host と通信する stdio サーバーを起動")
	fmt.Fprintln(w, "  mcp status                 MCP サーバーの状態確認")
	fmt.Fprintln(w, "")
	fmt.Fprintln(w, "オプション:")
	fmt.Fprintln(w, "  --json                     機械可読な JSON 形式で出力")
	fmt.Fprintln(w, "  --help, -h                 ヘルプを表示")
}
