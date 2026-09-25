package main

import (
	"bytes"
	"fmt"
	"runtime"
	"testing"
	"time"
)

// TUI描画フレーム性能を検証する
func TestTUIFrameRenderLatency(t *testing.T) {
	state := appState{screen: traceScreen, noClear: true, traceIndex: 2}
	iterations := 100

	var memStatsBefore runtime.MemStats
	runtime.ReadMemStats(&memStatsBefore)

	startTime := time.Now()
	var buffer bytes.Buffer

	for i := 0; i < iterations; i++ {
		buffer.Reset()
		if err := render(state, &buffer); err != nil {
			t.Fatalf("render error at %d: %v", i, err)
		}
	}

	totalDuration := time.Since(startTime)
	avgMicroseconds := totalDuration.Microseconds() / int64(iterations)

	var memStatsAfter runtime.MemStats
	runtime.ReadMemStats(&memStatsAfter)
	allocDiffKB := (memStatsAfter.TotalAlloc - memStatsBefore.TotalAlloc) / 1024

	fmt.Printf(`{"test": "TestTUIFrameRenderLatency", "iterations": %d, "total_ms": %d, "avg_frame_us": %d, "alloc_kb": %d}`+"\n",
		iterations, totalDuration.Milliseconds(), avgMicroseconds, allocDiffKB)

	// 1フレームあたり16ミリ秒(16000マイクロ秒=60FPS水準)未満であることを検証
	if avgMicroseconds > 16000 {
		t.Errorf("frame latency too high: %d us (expected < 16000 us for 60fps)", avgMicroseconds)
	}
}

// キー連打時の状態遷移速度を測る
func TestTUIEventLoopKeyLatency(t *testing.T) {
	state := appState{screen: traceScreen, traceIndex: 0}
	operations := 1000

	startTime := time.Now()
	for i := 0; i < operations; i++ {
		key := "down"
		if i%2 == 1 {
			key = "up"
		}
		var done bool
		state, done = nextState(state, key)
		if done {
			t.Fatal("unexpected exit")
		}
	}
	totalDuration := time.Since(startTime)
	avgNanoseconds := totalDuration.Nanoseconds() / int64(operations)

	fmt.Printf(`{"test": "TestTUIEventLoopKeyLatency", "operations": %d, "total_us": %d, "avg_key_ns": %d}`+"\n",
		operations, totalDuration.Microseconds(), avgNanoseconds)

	// 1キー入力の処理時間が1ミリ秒(1,000,000ns)未満であることを検証
	if avgNanoseconds > 1000000 {
		t.Errorf("key processing latency too high: %d ns", avgNanoseconds)
	}
}
