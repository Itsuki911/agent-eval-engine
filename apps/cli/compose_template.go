package main

import (
	"os"
	"path/filepath"
)

// GHCR の事前ビルド済み Docker イメージを使用するスタンドアロン Compose テンプレート
const defaultStandaloneComposeYAML = `# Agent Eval Engine - スタンドアロン実行用 Compose 定義
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-agent_eval}
      POSTGRES_USER: ${POSTGRES_USER:-agent_eval}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-local-development-password}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - postgres_data:/var/lib/postgresql/data

  engine:
    profiles: ["engine"]
    image: ${AGENT_EVAL_IMAGE:-ghcr.io/itsuki911/agent-eval-engine:latest}
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-agent_eval}:${POSTGRES_PASSWORD:-local-development-password}@db:5432/${POSTGRES_DB:-agent_eval}
      TEST_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-agent_eval}:${POSTGRES_PASSWORD:-local-development-password}@db:5432/agent_eval_test
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
      PYTHONPATH: /workspace:/workspace/packages/core
    depends_on:
      db:
        condition: service_healthy

  mcp:
    profiles: ["mcp"]
    image: ${AGENT_EVAL_IMAGE:-ghcr.io/itsuki911/agent-eval-engine:latest}
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-agent_eval}:${POSTGRES_PASSWORD:-local-development-password}@db:5432/${POSTGRES_DB:-agent_eval}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY:-}
      AGENT_EVAL_MCP_ALLOW_LIVE: ${AGENT_EVAL_MCP_ALLOW_LIVE:-0}
      PYTHONPATH: /workspace:/workspace/packages/core
    depends_on:
      db:
        condition: service_healthy
    stdin_open: true
    command: ["sh", "-c", "while :; do sleep 3600; done"]

volumes:
  postgres_data:
`

// 利用者データディレクトリ内にスタンドアロン Compose ファイルを配置する
func ensureStandaloneCompose(dataRoot string) error {
	composePath := filepath.Join(dataRoot, "docker-compose.yml")
	if _, err := os.Stat(composePath); err == nil {
		return nil
	}
	return os.WriteFile(composePath, []byte(defaultStandaloneComposeYAML), 0644)
}
