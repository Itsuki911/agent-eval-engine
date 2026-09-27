package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// 正常なJSONLトレース検証をテストする
func TestValidateTraceSuccess(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "agent-eval-trace-valid-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempDir)

	content := `{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-PY-001","agent_name":"codex-cli","model":"example-model"}
{"record_type":"event","sequence":0,"event_type":"user_prompt","actor":"user","payload":{"content":"Fix the bug."}}
{"record_type":"event","sequence":1,"event_type":"tool_call","payload":{"tool":"read","path":"main.py"}}
{"record_type":"result","status":"completed","task_success":true,"exit_code":0,"final_state":{"changed_files":["main.py"]}}
`
	filePath := filepath.Join(tempDir, "trace.jsonl")
	if err := os.WriteFile(filePath, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}

	res, err := validateTraceFile(filePath)
	if err != nil {
		t.Fatalf("expected valid trace, got err: %v", err)
	}
	if res.AdapterType != "codex" || res.EventCount != 2 || !res.TaskSuccess {
		t.Fatalf("unexpected validation result: %+v", res)
	}
}

// 不正なJSONL（run欠落、result欠落、sequence不連続）をテストする
func TestValidateTraceStructuralErrors(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "agent-eval-trace-invalid-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempDir)

	// 先頭が run でない
	noRun := `{"record_type":"event","sequence":0,"event_type":"user_prompt","payload":{"content":"Hi"}}
{"record_type":"result","status":"completed","task_success":true}
`
	p1 := filepath.Join(tempDir, "no-run.jsonl")
	os.WriteFile(p1, []byte(noRun), 0644)
	_, err = validateTraceFile(p1)
	if err == nil || !strings.Contains(err.Error(), "先頭") {
		t.Fatalf("expected no-run error, got %v", err)
	}

	// 末尾が result でない
	noResult := `{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-001","agent_name":"agent"}
{"record_type":"event","sequence":0,"event_type":"user_prompt","payload":{"content":"Hi"}}
`
	p2 := filepath.Join(tempDir, "no-result.jsonl")
	os.WriteFile(p2, []byte(noResult), 0644)
	_, err = validateTraceFile(p2)
	if err == nil || !strings.Contains(err.Error(), "末尾") {
		t.Fatalf("expected no-result error, got %v", err)
	}

	// sequence 不連続
	badSeq := `{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-001","agent_name":"agent"}
{"record_type":"event","sequence":0,"event_type":"user_prompt","payload":{"content":"Hi"}}
{"record_type":"event","sequence":5,"event_type":"tool_call","payload":{"tool":"read"}}
{"record_type":"result","status":"completed","task_success":true}
`
	p3 := filepath.Join(tempDir, "bad-seq.jsonl")
	os.WriteFile(p3, []byte(badSeq), 0644)
	_, err = validateTraceFile(p3)
	if err == nil || !strings.Contains(err.Error(), "sequence") {
		t.Fatalf("expected bad sequence error, got %v", err)
	}
}

// 秘密情報を含むJSONLの拒否をテストする
func TestValidateTraceSecretRejection(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "agent-eval-trace-secret-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempDir)

	secretJSONL := `{"record_type":"run","adapter_type":"codex","benchmark_id":"COD-001","agent_name":"agent"}
{"record_type":"event","sequence":0,"event_type":"tool_call","payload":{"tool":"http","api_key":"sk-secret-token"}}
{"record_type":"result","status":"completed","task_success":true}
`
	filePath := filepath.Join(tempDir, "secret.jsonl")
	os.WriteFile(filePath, []byte(secretJSONL), 0644)

	_, err = validateTraceFile(filePath)
	if err == nil || !strings.Contains(err.Error(), "秘密情報") {
		t.Fatalf("expected secret rejection error, got %v", err)
	}
}

// 拡張子およびファイルサイズ・行数制限をテストする
func TestValidateTraceLimits(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "agent-eval-trace-limits-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tempDir)

	// 非 .jsonl 拡張子
	badExt := filepath.Join(tempDir, "trace.txt")
	os.WriteFile(badExt, []byte("data"), 0644)
	_, err = validateTraceFile(badExt)
	if err == nil || !strings.Contains(err.Error(), ".jsonl") {
		t.Fatalf("expected .jsonl extension error, got %v", err)
	}
}
