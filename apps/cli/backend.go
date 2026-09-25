package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Python境界の実行情報を表す
type backendClient struct {
	python string
	root   string
}

// DB実行一覧の値を表す
type backendRun struct {
	RunID      string   `json:"run_id"`
	Benchmark  string   `json:"benchmark_id"`
	Status     string   `json:"status"`
	Provider   string   `json:"provider"`
	Model      string   `json:"model"`
	CostUSD    *float64 `json:"llm_cost_usd"`
	StartedAt  string   `json:"started_at"`
	FinishedAt string   `json:"finished_at"`
}

// DBイベントの値を表す
type backendEvent struct {
	Sequence  int            `json:"sequence"`
	EventType string         `json:"event_type"`
	Actor     string         `json:"actor"`
	Payload   map[string]any `json:"payload"`
	Error     map[string]any `json:"error"`
}

// DB実行詳細の値を表す
type backendDetail struct {
	RunID       string          `json:"run_id"`
	Benchmark   string          `json:"benchmark_id"`
	Status      string          `json:"status"`
	Provider    string          `json:"provider"`
	Model       string          `json:"model"`
	CostUSD     *float64        `json:"llm_cost_usd"`
	Events      []backendEvent  `json:"events"`
	Metrics     []backendMetric `json:"metrics"`
	Evaluations []backendResult `json:"evaluations"`
}

// 評価指標の値を表す
type backendMetric struct {
	Category string  `json:"category"`
	Name     string  `json:"name"`
	Value    float64 `json:"value"`
	Unit     string  `json:"unit"`
}

// 評価判定の値を表す
type backendResult struct {
	Status string   `json:"status"`
	Score  *float64 `json:"score"`
}

// benchmark候補の値を表す
type backendBenchmark struct {
	ID     string `json:"id"`
	Title  string `json:"title"`
	Family string `json:"family"`
	Path   string `json:"path"`
}

// Python進捗イベントを表す
type backendProgress struct {
	Type      string `json:"type"`
	Sequence  int    `json:"sequence"`
	EventType string `json:"event_type"`
	Status    string `json:"status"`
	ErrorType string `json:"error_type"`
}

// Python実行結果を表す
type backendRunResult struct {
	RunID       string          `json:"run_id"`
	Status      string          `json:"status"`
	BenchmarkID string          `json:"benchmark_id"`
	EventCount  int             `json:"event_count"`
	CostUSD     *float64        `json:"llm_cost_usd"`
	Metrics     []backendMetric `json:"metrics"`
}

// 比較指標の値を表す
type backendComparisonMetric struct {
	Name       string   `json:"name"`
	Left       *float64 `json:"left"`
	Right      *float64 `json:"right"`
	Difference float64  `json:"difference"`
}

// 実行比較の値を表す
type backendComparison struct {
	LeftRunID  string                    `json:"left_run_id"`
	RightRunID string                    `json:"right_run_id"`
	Metrics    []backendComparisonMetric `json:"metrics"`
}

// Python実行パスを初期化する
func newBackendClient() backendClient {
	root := os.Getenv("AGENT_EVAL_ROOT")
	if root == "" {
		root = "."
	}
	python := os.Getenv("AGENT_EVAL_PYTHON")
	if python == "" {
		python = "python"
	}
	return backendClient{python: python, root: root}
}

// Python境界を実行してJSONを返す
func (client backendClient) execute(ctx context.Context, args []string, onProgress func(backendProgress)) ([]byte, error) {
	script := filepath.Join(client.root, "scripts", "tui_backend.py")
	commandArgs := append([]string{script}, args...)
	command := exec.CommandContext(ctx, client.python, commandArgs...)
	command.Dir = client.root
	stdout, err := command.StdoutPipe()
	if err != nil {
		return nil, err
	}
	stderr, err := command.StderrPipe()
	if err != nil {
		return nil, err
	}
	if err := command.Start(); err != nil {
		return nil, err
	}
	diagnostics := make(chan string, 1)
	go scanProgress(stderr, onProgress, diagnostics)
	output, readErr := io.ReadAll(stdout)
	waitErr := command.Wait()
	diagnostic := <-diagnostics
	if readErr != nil {
		return nil, readErr
	}
	if waitErr != nil {
		if diagnostic != "" {
			return nil, fmt.Errorf("python backend failed: %s", diagnostic)
		}
		return nil, fmt.Errorf("python backend failed: %w", waitErr)
	}
	return output, nil
}

// 標準エラーの進捗を読み取る
func scanProgress(reader io.Reader, onProgress func(backendProgress), done chan<- string) {
	scanner := bufio.NewScanner(reader)
	diagnostics := make([]string, 0)
	for scanner.Scan() {
		line := scanner.Text()
		var progress backendProgress
		if json.Unmarshal([]byte(line), &progress) == nil && (progress.Type == "progress" || progress.Type == "error") {
			if onProgress != nil {
				onProgress(progress)
			}
			continue
		}
		if len(diagnostics) < 3 {
			diagnostics = append(diagnostics, line)
		}
	}
	done <- strings.Join(diagnostics, " | ")
}

// マイグレーションを適用する
func (client backendClient) migrate(ctx context.Context) error {
	_, err := client.execute(ctx, []string{"migrate"}, nil)
	return err
}

// 保存済み実行を取得する
func (client backendClient) listRuns(ctx context.Context) ([]backendRun, error) {
	output, err := client.execute(ctx, []string{"list-runs"}, nil)
	if err != nil {
		return nil, err
	}
	var response struct {
		Runs []backendRun `json:"runs"`
	}
	if err := json.Unmarshal(output, &response); err != nil {
		return nil, err
	}
	return response.Runs, nil
}

// 指定実行の詳細を取得する
func (client backendClient) showRun(ctx context.Context, runID string) (backendDetail, error) {
	output, err := client.execute(ctx, []string{"show-run", "--run-id", runID}, nil)
	if err != nil {
		return backendDetail{}, err
	}
	var response backendDetail
	if err := json.Unmarshal(output, &response); err != nil {
		return backendDetail{}, err
	}
	return response, nil
}

// benchmark候補を取得する
func (client backendClient) listBenchmarks(ctx context.Context) ([]backendBenchmark, error) {
	output, err := client.execute(ctx, []string{"list-benchmarks"}, nil)
	if err != nil {
		return nil, err
	}
	var response struct {
		Benchmarks []backendBenchmark `json:"benchmarks"`
	}
	if err := json.Unmarshal(output, &response); err != nil {
		return nil, err
	}
	return response.Benchmarks, nil
}

// 指定実行を比較する
func (client backendClient) compare(ctx context.Context, left string, right string) (backendComparison, error) {
	output, err := client.execute(ctx, []string{"compare", "--left", left, "--right", right}, nil)
	if err != nil {
		return backendComparison{}, err
	}
	var response backendComparison
	if err := json.Unmarshal(output, &response); err != nil {
		return backendComparison{}, err
	}
	return response, nil
}

// 評価処理を開始する
func (client backendClient) run(ctx context.Context, benchmark string, onProgress func(backendProgress)) (backendRunResult, error) {
	output, err := client.execute(ctx, []string{"run", "--benchmark", benchmark}, onProgress)
	if err != nil {
		return backendRunResult{}, err
	}
	var response backendRunResult
	if err := json.Unmarshal(output, &response); err != nil {
		return backendRunResult{}, err
	}
	return response, nil
}
