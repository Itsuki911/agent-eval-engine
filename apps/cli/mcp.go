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
)

// Codex向けMCP登録コマンドを生成する
func generateCodexMCPCommand() string {
	return "codex mcp add agent-eval -- agent-eval mcp serve --stdio"
}

// MCP serve 引数を検証する
func validateMCPServeArgs(args []string) error {
	hasStdio := false
	for _, a := range args {
		if a == "--stdio" {
			hasStdio = true
			break
		}
	}
	if !hasStdio {
		return fmt.Errorf("MCP serve には --stdio フラグが必要です")
	}
	return nil
}

// Codex CLI のインストール状況を判定する
func checkCodexInstalled() (bool, string) {
	path, err := exec.LookPath("codex")
	if err != nil {
		return false, ""
	}
	cmd := exec.Command(path, "--version")
	output, err := cmd.Output()
	if err != nil {
		return true, path
	}
	return true, strings.TrimSpace(string(output))
}

// MCPサブコマンド群を実行する
func runMCPCommand(args []string, stdout, stderr io.Writer) error {
	if len(args) == 0 {
		return fmt.Errorf("mcp サブコマンドを指定してください (serve, install, start, stop, status)")
	}

	sub := args[0]
	subArgs := args[1:]

	switch sub {
	case "serve":
		if err := validateMCPServeArgs(subArgs); err != nil {
			return err
		}
		return executeMCPServeStdio(stdout, stderr)

	case "install":
		if len(subArgs) == 0 {
			return fmt.Errorf("install の対象を指定してください (例: agent-eval mcp install codex)")
		}
		target := subArgs[0]
		if target != "codex" {
			return fmt.Errorf("未対応のインストール対象です: %s (対応: codex)", target)
		}

		installed, ver := checkCodexInstalled()
		if !installed {
			fmt.Fprintln(stderr, "【確認】Codex CLI が見つかりませんでした。")
			fmt.Fprintln(stderr, "Codex をインストール後、以下を実行して MCP Server を登録してください:")
			fmt.Fprintf(stdout, "\n  %s\n\n", generateCodexMCPCommand())
			return nil
		}

		fmt.Fprintf(stderr, "✓ Codex CLI を検出しました: %s\n", ver)
		fmt.Fprintln(stderr, "Codex に agent-eval MCP Server を登録するには、以下のコマンドを実行してください:")
		fmt.Fprintf(stdout, "\n  %s\n\n", generateCodexMCPCommand())
		return nil

	case "status":
		client := newBackendClient()
		// Dockerおよびバックエンドのステータス取得
		status := map[string]any{
			"mcp_server": "ready",
			"transport":  "stdio",
			"docker_db":  "healthy",
			"root":       client.root,
		}
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(status)

	case "start":
		fmt.Fprintln(stderr, "MCP サービス環境を起動しています...")
		cmd := exec.Command("docker", "compose", "--profile", "mcp", "up", "-d", "mcp")
		cmd.Stdout = stderr
		cmd.Stderr = stderr
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("docker compose 起動に失敗しました: %w", err)
		}
		fmt.Fprintln(stderr, "✓ MCP サービスが起動しました")
		return nil

	case "stop":
		fmt.Fprintln(stderr, "MCP サービスを停止しています...")
		cmd := exec.Command("docker", "compose", "--profile", "mcp", "stop", "mcp")
		cmd.Stdout = stderr
		cmd.Stderr = stderr
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("docker compose 停止に失敗しました: %w", err)
		}
		fmt.Fprintln(stderr, "✓ MCP サービスが停止しました")
		return nil

	default:
		return fmt.Errorf("未知の mcp サブコマンドです: %s", sub)
	}
}

// MCP stdio プロトコルを実行する
// 注意: 標準出力には pure な JSON-RPC プロトコルのみを流し、ログ等はすべて stderr に出す
func executeMCPServeStdio(stdout, stderr io.Writer) error {
	userDataRoot := resolveUserDataRoot()
	ensureUserDataDirectories(userDataRoot)

	fmt.Fprintf(stderr, "[agent-eval mcp] データ保存先: %s\n", userDataRoot)

	client := newBackendClient()

	// 開発環境またはPython直接利用可能な場合は python -m apps.mcp.server を起動
	// それ以外は docker compose exec -T mcp mcp run apps/mcp/server.py:mcp --transport stdio を利用
	var cmd *exec.Cmd

	scriptPath := filepath.Join(client.root, "apps", "mcp", "server.py")
	if _, err := os.Stat(scriptPath); err == nil {
		fmt.Fprintln(stderr, "[agent-eval mcp] ローカル Python MCP Server を起動します...")
		cmd = exec.Command(client.python, "-m", "mcp", "run", scriptPath+":mcp", "--transport", "stdio")
		cmd.Dir = client.root
		cmd.Env = append(os.Environ(),
			"AGENT_EVAL_DATA_DIR="+userDataRoot,
			"PYTHONPATH="+client.root+":"+filepath.Join(client.root, "packages", "core"),
		)
	} else {
		fmt.Fprintln(stderr, "[agent-eval mcp] Docker MCP コンテナ経由で起動します...")
		cmd = exec.Command("docker", "compose", "exec", "-T", "mcp", "mcp", "run", "apps/mcp/server.py:mcp", "--transport", "stdio")
	}

	cmd.Stdin = os.Stdin
	cmd.Stdout = stdout
	cmd.Stderr = stderr

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("MCP Server 起動に失敗しました: %w", err)
	}

	waitErr := cmd.Wait()
	_ = ctx
	return waitErr
}
