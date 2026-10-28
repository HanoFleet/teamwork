package health

import (
	"context"
	"errors"
	"testing"
	"time"
)

func fixedNow() time.Time { return time.Date(2026, 10, 28, 12, 0, 0, 0, time.UTC) }

func TestLive(t *testing.T) {
	c := Checker{Version: "v-test", Now: fixedNow}
	got := c.Live()
	if got.Status != "ok" || got.Version != "v-test" || got.Time != "2026-10-28T12:00:00Z" {
		t.Fatalf("live = %+v", got)
	}
}

func TestReadyAllUp(t *testing.T) {
	c := Checker{
		Version:     "v-test",
		Now:         fixedNow,
		EmbeddingOK: true,
		PingDB:      func(context.Context) error { return nil },
		QdrantOK:    func(context.Context) bool { return true },
	}
	got, ok := c.Ready(context.Background())
	if !ok || got.Status != "ready" || !got.Checks["db"] || !got.Checks["qdrant"] || !got.Checks["embedding"] {
		t.Fatalf("ready = %+v ok=%v", got, ok)
	}
}

func TestReadyDatabaseDown(t *testing.T) {
	c := Checker{
		Version:     "v-test",
		Now:         fixedNow,
		EmbeddingOK: true,
		PingDB:      func(context.Context) error { return errors.New("down") },
		QdrantOK:    func(context.Context) bool { return true },
	}
	got, ok := c.Ready(context.Background())
	if ok || got.Status != "not_ready" || got.Checks["db"] || !got.Checks["qdrant"] {
		t.Fatalf("ready = %+v ok=%v", got, ok)
	}
}

func TestReadyQdrantDown(t *testing.T) {
	c := Checker{
		Version:     "v-test",
		Now:         fixedNow,
		EmbeddingOK: true,
		PingDB:      func(context.Context) error { return nil },
		QdrantOK:    func(context.Context) bool { return false },
	}
	got, ok := c.Ready(context.Background())
	if ok || got.Checks["qdrant"] {
		t.Fatalf("ready = %+v ok=%v", got, ok)
	}
}
