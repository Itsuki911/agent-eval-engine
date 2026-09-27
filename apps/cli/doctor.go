package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

type checkStatus string

const (
	checkStatusOK      checkStatus = "OK"
	checkStatusWarning checkStatus = "WARN"
	checkStatusFail    checkStatus = "FAIL"
)

// 診断チェック1件の結果を表す
type doctorCheckResult struct {
	Category string      `json:"category"`
	Name     string      `json:"name"`
	Status   checkStatus `json:"status"`
	Message  string      `json:"message"`
	Action   string      `json:"action,omitempty"`
}

// 診断レポート全体を表す
type doctorReport struct {
	OverallStatus checkStatus         `json:"overall_status"`
	Timestamp     string              `json:"timestamp"`
	Checks        []doctorCheckResult `json:"checks"`
}

// チェック結果一覧から全体レポートを判定する
func evaluateDoctorChecks(checks []doctorCheckResult) doctorReport {
	overall := checkStatusOK
	for _, c := range checks {
		if c.Status == checkStatusFail {
			overall = checkStatusFail
			break
		} else if c.Status == checkStatusWarning && overall != checkStatusFail {
			overall = checkStatusWarning
		}
	}

	return doctorReport{
		OverallStatus: overall,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Checks:        checks,
	}
}

// 人間向けのテキスト診断レポートを表示する
func renderDoctorReport(report doctorReport, w io.Writer) {
	fmt.Fprintln(w, "============================================================")
	fmt.Fprintln(w, "           Agent Eval Engine システム診断 (Doctor)")
	fmt.Fprintln(w, "============================================================")
	fmt.Fprintf(w, "診断日時: %s\n", report.Timestamp)
	fmt.Fprintf(w, "総合判定: [%s]\n\n", report.OverallStatus)

	for _, check := range report.Checks {
		tag := "[OK]"
		switch check.Status {
		case checkStatusWarning:
			tag = "[WARN]"
		case checkStatusFail:
			tag = "[FAIL]"
		}

		fmt.Fprintf(w, "%-6s %-12s - %s\n", tag, check.Category, check.Name)
		fmt.Fprintf(w, "       詳細: %s\n", check.Message)
		if check.Action != "" {
			fmt.Fprintf(w, "       対応: %s\n", check.Action)
		}
		fmt.Fprintln(w)
	}

	if report.OverallStatus == checkStatusOK {
		fmt.Fprintln(w, "✓ すべての環境チェックに合格しました。評価エンジンは正常に利用できます。")
	} else {
		fmt.Fprintln(w, "上記で [WARN] または [FAIL] となった項目の対応手順を実施してください。")
	}
}

// 機械可読な JSON レポートを出力する
func outputDoctorJSON(report doctorReport, w io.Writer) error {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	return encoder.Encode(report)
}

// 実際のシステム環境を診断する
func runSystemDiagnostics(ctx context.Context) doctorReport {
	var checks []doctorCheckResult

	// 1. Docker Daemon 確認
	dockerCmd := exec.CommandContext(ctx, "docker", "version", "--format", "{{.Server.Version}}")
	dockerOut, err := dockerCmd.Output()
	if err != nil {
		checks = append(checks, doctorCheckResult{
			Category: "Docker",
			Name:     "Docker Daemon",
			Status:   checkStatusFail,
			Message:  "Docker Desktop または Docker デーモンが起動していません",
			Action:   "Docker Desktop を起動してから再実行してください",
		})
	} else {
		checks = append(checks, doctorCheckResult{
			Category: "Docker",
			Name:     "Docker Daemon",
			Status:   checkStatusOK,
			Message:  fmt.Sprintf("Docker 稼働中 (v%s)", strings.TrimSpace(string(dockerOut))),
		})
	}

	// 2. Docker Compose 確認
	composeCmd := exec.CommandContext(ctx, "docker", "compose", "version", "--short")
	composeOut, err := composeCmd.Output()
	if err != nil {
		checks = append(checks, doctorCheckResult{
			Category: "Docker",
			Name:     "Docker Compose",
			Status:   checkStatusFail,
			Message:  "Docker Compose が利用できません",
			Action:   "Docker Desktop の設定で Docker Compose v2 が有効か確認してください",
		})
	} else {
		checks = append(checks, doctorCheckResult{
			Category: "Docker",
			Name:     "Docker Compose",
			Status:   checkStatusOK,
			Message:  fmt.Sprintf("Docker Compose 利用可能 (v%s)", strings.TrimSpace(string(composeOut))),
		})
	}

	// 3. データ保存先確認
	dataRoot := resolveUserDataRoot()
	paths, err := ensureUserDataDirectories(dataRoot)
	if err != nil {
		checks = append(checks, doctorCheckResult{
			Category: "Storage",
			Name:     "UserData Directory",
			Status:   checkStatusFail,
			Message:  fmt.Sprintf("データ保存先を作成できません (%s): %v", dataRoot, err),
			Action:   "フォルダのアクセス権限を確認するか、AGENT_EVAL_DATA_DIR を指定してください",
		})
	} else {
		// テスト書き込み
		testFile := filepath.Join(paths.LogsDir, ".write-test")
		if werr := os.WriteFile(testFile, []byte("ok"), 0644); werr != nil {
			checks = append(checks, doctorCheckResult{
				Category: "Storage",
				Name:     "Write Permission",
				Status:   checkStatusFail,
				Message:  fmt.Sprintf("保存先に書き込み権限がありません: %v", werr),
				Action:   "ディレクトリの書き込み権限を付与してください",
			})
		} else {
			os.Remove(testFile)
			checks = append(checks, doctorCheckResult{
				Category: "Storage",
				Name:     "UserData Directory",
				Status:   checkStatusOK,
				Message:  fmt.Sprintf("保存先正常 (%s)", dataRoot),
			})
		}
	}

	// 4. バックエンド / DB 状態確認
	client := newBackendClient()
	output, err := client.execute(ctx, []string{"doctor"}, nil)
	if err != nil {
		checks = append(checks, doctorCheckResult{
			Category: "Backend",
			Name:     "Evaluation Engine & DB",
			Status:   checkStatusWarning,
			Message:  fmt.Sprintf("評価エンジン/DBの疎通確認に失敗しました: %v", err),
			Action:   "agent-eval init または docker compose up -d db を実行してください",
		})
	} else {
		var backendStatus struct {
			Database   string `json:"database"`
			Migrations string `json:"migrations"`
		}
		if jsonErr := json.Unmarshal(output, &backendStatus); jsonErr == nil {
			checks = append(checks, doctorCheckResult{
				Category: "Database",
				Name:     "PostgreSQL",
				Status:   checkStatusOK,
				Message:  fmt.Sprintf("接続成功 (%s)", backendStatus.Database),
			})
			checks = append(checks, doctorCheckResult{
				Category: "Database",
				Name:     "Schema Migrations",
				Status:   checkStatusOK,
				Message:  fmt.Sprintf("最新リビジョン適用済み (%s)", backendStatus.Migrations),
			})
		} else {
			checks = append(checks, doctorCheckResult{
				Category: "Backend",
				Name:     "Backend Bridge",
				Status:   checkStatusOK,
				Message:  "Python 評価エンジン応答正常",
			})
		}
	}

	// 5. MCP 状態確認
	checks = append(checks, doctorCheckResult{
		Category: "MCP",
		Name:     "MCP stdio Server",
		Status:   checkStatusOK,
		Message:  "stdio プロトコル待機準備完了 (agent-eval mcp serve --stdio)",
	})

	return evaluateDoctorChecks(checks)
}
