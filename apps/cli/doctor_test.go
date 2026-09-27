package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

// doctor の診断結果集約をテストする
func TestDoctorReportEvaluation(t *testing.T) {
	checks := []doctorCheckResult{
		{
			Category: "Docker",
			Name:     "Docker Daemon",
			Status:   checkStatusOK,
			Message:  "Docker は正常に稼働しています (Docker 29.7.2)",
		},
		{
			Category: "Database",
			Name:     "PostgreSQL",
			Status:   checkStatusWarning,
			Message:  "DB コンテナが停止しています",
			Action:   "agent-eval init または docker compose up -d db を実行してください",
		},
		{
			Category: "Storage",
			Name:     "Data Directory",
			Status:   checkStatusOK,
			Message:  "保存先ディレクトリへの書き込みが可能です",
		},
	}

	report := evaluateDoctorChecks(checks)
	if report.OverallStatus != checkStatusWarning {
		t.Fatalf("expected overall warning, got %s", report.OverallStatus)
	}

	var buf bytes.Buffer
	renderDoctorReport(report, &buf)
	rendered := buf.String()

	if !strings.Contains(rendered, "[OK]") || !strings.Contains(rendered, "[WARN]") {
		t.Fatalf("rendered report missing status markers: %s", rendered)
	}
	if !strings.Contains(rendered, "DB コンテナが停止しています") {
		t.Fatalf("rendered report missing warning message: %s", rendered)
	}
}

// doctor の --json 出力をテストする
func TestDoctorReportJSON(t *testing.T) {
	checks := []doctorCheckResult{
		{
			Category: "Docker",
			Name:     "Docker Daemon",
			Status:   checkStatusOK,
			Message:  "Docker is running",
		},
	}
	report := evaluateDoctorChecks(checks)

	var buf bytes.Buffer
	outputDoctorJSON(report, &buf)

	var data map[string]any
	if err := json.Unmarshal(buf.Bytes(), &data); err != nil {
		t.Fatalf("invalid json from outputDoctorJSON: %v", err)
	}

	if data["overall_status"] != "OK" {
		t.Fatalf("unexpected overall_status: %v", data["overall_status"])
	}
	checksList, ok := data["checks"].([]any)
	if !ok || len(checksList) == 0 {
		t.Fatalf("expected checks array, got %v", data["checks"])
	}
}
