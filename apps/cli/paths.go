package main

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

// 利用者データパス群を表す
type userDataPaths struct {
	Root           string `json:"root"`
	ConfigDir      string `json:"config_dir"`
	DatasetsDir    string `json:"datasets_dir"`
	AgentTracesDir string `json:"agent_traces_dir"`
	ExportsDir     string `json:"exports_dir"`
	LogsDir        string `json:"logs_dir"`
	DiagnosticsDir string `json:"diagnostics_dir"`
}

// OSごとの利用者データ保存先ルートを解決する
func resolveUserDataRoot() string {
	if custom := os.Getenv("AGENT_EVAL_DATA_DIR"); custom != "" {
		return filepath.Clean(custom)
	}

	switch runtime.GOOS {
	case "windows":
		if localAppData := os.Getenv("LOCALAPPDATA"); localAppData != "" {
			return filepath.Join(localAppData, "AgentEvalEngine")
		}
		if userProfile := os.Getenv("USERPROFILE"); userProfile != "" {
			return filepath.Join(userProfile, "AppData", "Local", "AgentEvalEngine")
		}
		return filepath.Join(".", "local-data")
	case "darwin":
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, "Library", "Application Support", "AgentEvalEngine")
		}
		return filepath.Join(".", "local-data")
	default:
		// linux / unix
		if xdg := os.Getenv("XDG_DATA_HOME"); xdg != "" {
			return filepath.Join(xdg, "agent-eval-engine")
		}
		if home := os.Getenv("HOME"); home != "" {
			return filepath.Join(home, ".local", "share", "agent-eval-engine")
		}
		return filepath.Join(".", "local-data")
	}
}

// 利用者データディレクトリ群を作成してパスを返す
func ensureUserDataDirectories(root string) (userDataPaths, error) {
	cleanRoot := filepath.Clean(root)
	paths := userDataPaths{
		Root:           cleanRoot,
		ConfigDir:      filepath.Join(cleanRoot, "config"),
		DatasetsDir:    filepath.Join(cleanRoot, "datasets"),
		AgentTracesDir: filepath.Join(cleanRoot, "agent-traces"),
		ExportsDir:     filepath.Join(cleanRoot, "exports"),
		LogsDir:        filepath.Join(cleanRoot, "logs"),
		DiagnosticsDir: filepath.Join(cleanRoot, "diagnostics"),
	}

	dirs := []string{
		paths.Root,
		paths.ConfigDir,
		paths.DatasetsDir,
		paths.AgentTracesDir,
		paths.ExportsDir,
		paths.LogsDir,
		paths.DiagnosticsDir,
	}

	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return userDataPaths{}, fmt.Errorf("保存先ディレクトリ作成に失敗しました (%s): %w", dir, err)
		}
	}

	_ = ensureStandaloneCompose(paths.Root)

	return paths, nil
}

// 利用者データパス内の安全なパスを解決し、パストラバーサルを拒否する
func resolveUserPath(root, relPath string) (string, error) {
	cleanRoot := filepath.Clean(root)
	// 相対パスを正規化
	target := filepath.Clean(filepath.Join(cleanRoot, relPath))

	// root 配下にあるか検証
	rel, err := filepath.Rel(cleanRoot, target)
	if err != nil || strings.HasPrefix(rel, "..") || rel == "." && relPath != "." && relPath != "" {
		return "", fmt.Errorf("許可されていないパスへのアクセスです: %s", relPath)
	}

	return target, nil
}

// 開発リポジトリのルートパスを保存する
func saveConfiguredRepoRoot(dataRoot, repoRoot string) error {
	if repoRoot == "" {
		return nil
	}
	cleanRepo := filepath.Clean(repoRoot)
	configDir := filepath.Join(dataRoot, "config")
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(configDir, "repo_root.txt"), []byte(cleanRepo), 0644)
}

// 保存された開発リポジトリのルートパスを取得する
func resolveConfiguredRepoRoot(dataRoot string) string {
	content, err := os.ReadFile(filepath.Join(dataRoot, "config", "repo_root.txt"))
	if err != nil {
		return ""
	}
	trimmed := strings.TrimSpace(string(content))
	if trimmed == "" {
		return ""
	}
	return filepath.Clean(trimmed)
}
