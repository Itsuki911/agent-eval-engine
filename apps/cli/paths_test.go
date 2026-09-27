package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

// OSごとの利用者データ保存先解決をテストする
func TestResolveUserDataRoot(t *testing.T) {
	// 環境変数が指定されている場合は最優先されること
	customDir := filepath.Join(os.TempDir(), "agent-eval-custom-test")
	t.Setenv("AGENT_EVAL_DATA_DIR", customDir)
	resolved := resolveUserDataRoot()
	if resolved != filepath.Clean(customDir) {
		t.Fatalf("expected customDir %s, got %s", customDir, resolved)
	}

	// 環境変数をクリアしてOSごとのデフォルトを確認
	t.Setenv("AGENT_EVAL_DATA_DIR", "")
	defaultPath := resolveUserDataRoot()
	if defaultPath == "" {
		t.Fatal("default path should not be empty")
	}

	switch runtime.GOOS {
	case "windows":
		localAppData := os.Getenv("LOCALAPPDATA")
		if localAppData != "" {
			expected := filepath.Join(localAppData, "AgentEvalEngine")
			if defaultPath != expected {
				t.Fatalf("windows default path: expected %s, got %s", expected, defaultPath)
			}
		}
	case "darwin":
		home := os.Getenv("HOME")
		if home != "" {
			expected := filepath.Join(home, "Library", "Application Support", "AgentEvalEngine")
			if defaultPath != expected {
				t.Fatalf("darwin default path: expected %s, got %s", expected, defaultPath)
			}
		}
	default:
		// linux
		home := os.Getenv("HOME")
		if home != "" {
			expected := filepath.Join(home, ".local", "share", "agent-eval-engine")
			if defaultPath != expected {
				t.Fatalf("linux default path: expected %s, got %s", expected, defaultPath)
			}
		}
	}
}

// 利用者データディレクトリの作成と構成をテストする
func TestEnsureUserDataDirectories(t *testing.T) {
	tempRoot, err := os.MkdirTemp("", "agent-eval-paths-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempRoot)

	paths, err := ensureUserDataDirectories(tempRoot)
	if err != nil {
		t.Fatalf("ensureUserDataDirectories failed: %v", err)
	}

	expectedDirs := []string{
		paths.ConfigDir,
		paths.DatasetsDir,
		paths.AgentTracesDir,
		paths.ExportsDir,
		paths.LogsDir,
		paths.DiagnosticsDir,
	}

	for _, dir := range expectedDirs {
		info, err := os.Stat(dir)
		if err != nil {
			t.Fatalf("directory does not exist: %s", dir)
		}
		if !info.IsDir() {
			t.Fatalf("path is not a directory: %s", dir)
		}
	}
}

// パストラバーサル防止をテストする
func TestResolveUserPathTraversal(t *testing.T) {
	tempRoot, err := os.MkdirTemp("", "agent-eval-traversal-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempRoot)

	// 正常な相対パス
	safe, err := resolveUserPath(tempRoot, "safe-file.jsonl")
	if err != nil {
		t.Fatalf("expected safe path to succeed: %v", err)
	}
	if !strings.HasPrefix(safe, filepath.Clean(tempRoot)) {
		t.Fatalf("safe path %s not under root %s", safe, tempRoot)
	}

	// パストラバーサル (..)
	_, err = resolveUserPath(tempRoot, "../escape.jsonl")
	if err == nil {
		t.Fatal("expected traversal attempt to fail, but it succeeded")
	}

	// 多重トラバーサル
	_, err = resolveUserPath(tempRoot, "sub/../../escape.jsonl")
	if err == nil {
		t.Fatal("expected nested traversal attempt to fail, but it succeeded")
	}
}
