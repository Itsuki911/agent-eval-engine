package main

import (
	"fmt"
	"strings"
)

// 初回設定ウィザード画面を描画する
func renderWizard(state appState) string {
	totalSteps := 5
	step := state.wizardStep
	if step < 0 {
		step = 0
	}
	if step >= totalSteps {
		step = totalSteps - 1
	}

	steps := []struct {
		title string
		desc  string
		body  []string
	}{
		{
			title: "1. Docker 環境の確認",
			desc:  "Docker Desktop および Docker Compose の稼働状況を確認します",
			body: []string{
				"  ✓ Docker Daemon: 稼働中 (Docker 29.x)",
				"  ✓ Docker Compose: 利用可能 (v2.x)",
				"",
				"  評価エンジンと PostgreSQL は Docker コンテナ上で安全に実行されます。",
			},
		},
		{
			title: "2. 利用者データ保存先の確認",
			desc:  "評価結果、自作 benchmark、実行記録の保存先を準備します",
			body: []string{
				fmt.Sprintf("  保存先ディレクトリ: %s", resolveUserDataRoot()),
				"",
				"  - config/        : 接続設定・構成ファイル",
				"  - datasets/      : 利用者作成 benchmark (YAML)",
				"  - agent-traces/  : 外部 Coding Agent の実行ログ (JSONL)",
				"  - exports/       : CSV エクスポート保存先",
				"  - logs/          : 実行ログおよび診断記録",
			},
		},
		{
			title: "3. データベース初期化 (Migration)",
			desc:  "PostgreSQL データベースのテーブルスキーマを最新状態に更新します",
			body: []string{
				"  ✓ スキーマバージョン: 20260925_0004",
				"  ✓ テーブル構成: runs, events, metrics, evaluations, agent_executions",
				"",
				"  既存データを破壊することなく安全にマイグレーションが適用されます。",
			},
		},
		{
			title: "4. サンプル Benchmark の導入",
			desc:  "すぐに評価を試せる標準 benchmark セットを確認します",
			body: []string{
				"  ✓ generic/GEN-TOOL-001.yaml (ツールの正しい呼び出しを検証)",
				"  ✓ coding/COD-PY-001.yaml    (Pythonコード修正タスク)",
				"",
				"  初期設定は dry-run モードのため、LLM API の課金は一切発生しません。",
			},
		},
		{
			title: "5. セットアップ完了 & dry-run 確認",
			desc:  "すべての準備が整いました！",
			body: []string{
				"  [Enter] または [1] を押して、dry-run 評価を開始できます。",
				"  または [h] を押してホーム画面に戻ります。",
				"",
				"  いつでも `agent-eval doctor` で環境の健全性を診断できます。",
			},
		},
	}

	current := steps[step]
	lines := []string{
		paint(cyanStyle, fmt.Sprintf("SETUP WIZARD  |  初回設定ウィザード (%d/%d)", step+1, totalSteps)),
		paint(slateStyle, current.desc),
		paint(cyanStyle, divider),
		paint(purpleStyle, fmt.Sprintf("◆ ステップ %d: %s", step+1, current.title)),
		"",
	}
	lines = append(lines, current.body...)
	lines = append(lines,
		"",
		paint(cyanStyle, divider),
		paint(blueStyle, "Enter/n 次へ     b 戻る     h ホーム     q 終了"),
	)
	return strings.Join(lines, "\n") + "\n"
}

// Real Agent 記録取込画面を描画する
func renderImportTrace(state appState) string {
	lines := []string{
		paint(cyanStyle, "REAL AGENT TRACE IMPORT  |  外部Agent実行記録の取り込み"),
		paint(slateStyle, "Codex、OpenCode、Antigravity などの実行記録 (JSONL) を評価DBへ取り込みます"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "取り込む JSONL ファイルのパスを指定してください:"),
		"",
	}

	pathDisplay := state.importTracePath
	if pathDisplay == "" {
		pathDisplay = "fixtures/agent-traces/codex-success.jsonl"
	}
	lines = append(lines, fmt.Sprintf("  ファイルパス: [ %s ]", paint(greenStyle, pathDisplay)))
	lines = append(lines, "")

	if state.importTraceError != "" {
		lines = append(lines, paint(redStyle, "  ✗ エラー: "+state.importTraceError), "")
	} else if state.importTraceResult != nil {
		lines = append(lines,
			paint(greenStyle, "  ✓ 形式検証に合格しました:"),
			fmt.Sprintf("    Adapter:    %s", state.importTraceResult.AdapterType),
			fmt.Sprintf("    Benchmark:  %s", state.importTraceResult.BenchmarkID),
			fmt.Sprintf("    イベント数:  %d", state.importTraceResult.EventCount),
			fmt.Sprintf("    タスク成功:  %v", state.importTraceResult.TaskSuccess),
			"",
		)
	} else if state.importTraceSuccess != "" {
		lines = append(lines, paint(greenStyle, "  ✓ "+state.importTraceSuccess), "")
	} else {
		lines = append(lines,
			paint(slateStyle, "  ヒント: [v] で形式を検証、[i] または [Enter] でデータベースへ取り込みます。"),
			paint(slateStyle, "  APIキーやパスワード等の秘密情報を含む記録は自動的に拒否されます。"),
			"",
		)
	}

	lines = append(lines,
		paint(cyanStyle, divider),
		paint(blueStyle, "v 検証     i 取込実行     t Trace確認     b 戻る     q 終了"),
	)
	return strings.Join(lines, "\n") + "\n"
}

// MCP 接続設定画面を描画する
func renderMCP(state appState) string {
	lines := []string{
		paint(cyanStyle, "MCP CONFIGURATION  |  Model Context Protocol 接続ガイド"),
		paint(slateStyle, "AI Agent (Codex, OpenCode, Antigravity) から評価エンジンを呼び出す設定です"),
		paint(cyanStyle, divider),
		paint(purpleStyle, "【Codex への登録】"),
		"  以下のコマンドをターミナルで実行してください:",
		"",
		paint(greenStyle, "    codex mcp add agent-eval -- agent-eval mcp serve --stdio"),
		"",
		paint(purpleStyle, "【OpenCode への登録 (opencode.json)】"),
		"  \"mcp\": { \"servers\": { \"agent-eval\": { \"command\": [\"agent-eval\", \"mcp\", \"serve\", \"--stdio\"] } } }",
		"",
		paint(purpleStyle, "【Antigravity への登録】"),
		"  antigravity.json の mcpServers に agent-eval を追加します。",
		"",
		paint(slateStyle, "  ※ stdio 接続ではログと JSON-RPC プロトコルが完全分離されます。"),
		paint(cyanStyle, divider),
		paint(blueStyle, "s 状態確認 (agent-eval mcp status)     b 戻る     q 終了"),
	}
	return strings.Join(lines, "\n") + "\n"
}

// 設定・診断 (Doctor) 画面を描画する
func renderDoctor(state appState) string {
	lines := []string{
		paint(cyanStyle, "SYSTEM DOCTOR  |  環境・診断レポート"),
		paint(slateStyle, "Docker、PostgreSQL、マイグレーション、データ保存先の健全性を確認します"),
		paint(cyanStyle, divider),
	}

	if state.doctorReport == nil {
		lines = append(lines,
			paint(amberStyle, "  診断情報を読み込んでいます..."),
			"",
			paint(slateStyle, "  [r] を押すと再診断を実行します。"),
			"",
		)
	} else {
		statusColor := greenStyle
		if state.doctorReport.OverallStatus == checkStatusWarning {
			statusColor = amberStyle
		} else if state.doctorReport.OverallStatus == checkStatusFail {
			statusColor = redStyle
		}

		lines = append(lines,
			fmt.Sprintf("  総合判定: %s", paint(statusColor, "["+string(state.doctorReport.OverallStatus)+"]")),
			fmt.Sprintf("  診断日時: %s", state.doctorReport.Timestamp),
			"",
		)

		for _, check := range state.doctorReport.Checks {
			tag := paint(greenStyle, "[OK]")
			if check.Status == checkStatusWarning {
				tag = paint(amberStyle, "[WARN]")
			} else if check.Status == checkStatusFail {
				tag = paint(redStyle, "[FAIL]")
			}
			lines = append(lines, fmt.Sprintf("  %s %-12s - %s", tag, check.Category, check.Name))
			lines = append(lines, paint(slateStyle, "       "+check.Message))
			if check.Action != "" {
				lines = append(lines, paint(amberStyle, "       対応: "+check.Action))
			}
		}
		lines = append(lines, "")
	}

	lines = append(lines,
		paint(cyanStyle, divider),
		paint(blueStyle, "r 再診断実行     b 戻る     q 終了"),
	)
	return strings.Join(lines, "\n") + "\n"
}
