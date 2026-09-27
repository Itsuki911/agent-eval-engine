package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// version コマンドの出力をテストする
func TestCommandVersion(t *testing.T) {
	// 通常出力（テキスト）
	var outBuf bytes.Buffer
	var errBuf bytes.Buffer
	err := executeCLI([]string{"version"}, &outBuf, &errBuf)
	if err != nil {
		t.Fatalf("version command failed: %v", err)
	}
	outStr := outBuf.String()
	if !strings.Contains(outStr, "Agent Eval Engine") || !strings.Contains(outStr, "version:") {
		t.Fatalf("unexpected version output: %s", outStr)
	}

	// JSON出力
	outBuf.Reset()
	errBuf.Reset()
	err = executeCLI([]string{"version", "--json"}, &outBuf, &errBuf)
	if err != nil {
		t.Fatalf("version --json failed: %v", err)
	}
	var data map[string]any
	if err := json.Unmarshal(outBuf.Bytes(), &data); err != nil {
		t.Fatalf("version --json did not return valid JSON: %v, raw: %s", err, outBuf.String())
	}
	if data["version"] == nil || data["schema_version"] == nil {
		t.Fatalf("version json missing keys: %v", data)
	}
}

// 不正なサブコマンドの拒否をテストする
func TestCommandUnknownSubcommand(t *testing.T) {
	var outBuf bytes.Buffer
	var errBuf bytes.Buffer
	err := executeCLI([]string{"nonexistent-command"}, &outBuf, &errBuf)
	if err == nil {
		t.Fatal("expected error for nonexistent command, but got nil")
	}

	errOutput := errBuf.String() + err.Error()
	if !strings.Contains(errOutput, "原因") || !strings.Contains(errOutput, "次の操作") {
		t.Fatalf("error message missing structured guidance: %s", errOutput)
	}
}

// 引数不足の拒否をテストする
func TestCommandMissingArguments(t *testing.T) {
	var outBuf bytes.Buffer
	var errBuf bytes.Buffer
	// run コマンドは benchmark-id が必須
	err := executeCLI([]string{"run"}, &outBuf, &errBuf)
	if err == nil {
		t.Fatal("expected error for run without benchmark-id, but got nil")
	}

	// trace コマンドは run-id が必須
	outBuf.Reset()
	errBuf.Reset()
	err = executeCLI([]string{"trace"}, &outBuf, &errBuf)
	if err == nil {
		t.Fatal("expected error for trace without run-id, but got nil")
	}

	// compare コマンドは 2つの run-id が必須
	outBuf.Reset()
	errBuf.Reset()
	err = executeCLI([]string{"compare", "only-one-id"}, &outBuf, &errBuf)
	if err == nil {
		t.Fatal("expected error for compare with only 1 argument, but got nil")
	}
}

// エラー案内フォーマットをテストする
func TestFormatUserError(t *testing.T) {
	formatted := formatUserError("Docker Desktop が起動していません", "Docker Desktop を起動してから再実行してください", "C:\\Users\\user\\AppData\\Local\\AgentEvalEngine\\logs\\doctor.log")
	if !strings.Contains(formatted, "【原因】") {
		t.Fatalf("missing cause: %s", formatted)
	}
	if !strings.Contains(formatted, "【次の操作】") {
		t.Fatalf("missing action: %s", formatted)
	}
	if !strings.Contains(formatted, "【詳細ログ】") {
		t.Fatalf("missing log: %s", formatted)
	}
}
