package main

import (
	"strings"
	"testing"
)

// Codex MCP 登録コマンドの生成をテストする
func TestGenerateCodexMCPCommand(t *testing.T) {
	cmd := generateCodexMCPCommand()
	expected := "codex mcp add agent-eval -- agent-eval mcp serve --stdio"
	if cmd != expected {
		t.Fatalf("expected '%s', got '%s'", expected, cmd)
	}
}

// MCP stdio 起動オプションの検証をテストする
func TestMCPServeFlags(t *testing.T) {
	// --stdio フラグ必須の確認
	err := validateMCPServeArgs([]string{})
	if err == nil || !strings.Contains(err.Error(), "--stdio") {
		t.Fatalf("expected error when --stdio is missing, got %v", err)
	}

	err = validateMCPServeArgs([]string{"--stdio"})
	if err != nil {
		t.Fatalf("expected valid with --stdio, got %v", err)
	}
}
