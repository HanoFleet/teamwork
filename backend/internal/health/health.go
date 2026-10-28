package health

import (
	"context"
	"time"
)

type Checker struct {
	PingDB      func(context.Context) error
	QdrantOK    func(context.Context) bool
	EmbeddingOK bool
	Version     string
	Now         func() time.Time
	Timeout     time.Duration
}

type Result struct {
	Status  string          `json:"status"`
	Version string          `json:"version"`
	Time    string          `json:"time"`
	Checks  map[string]bool `json:"checks,omitempty"`
}

func (c Checker) now() time.Time {
	if c.Now != nil {
		return c.Now().UTC()
	}
	return time.Now().UTC()
}

func (c Checker) version() string {
	if c.Version == "" {
		return "dev"
	}
	return c.Version
}

func (c Checker) Live() Result {
	return Result{Status: "ok", Version: c.version(), Time: c.now().Format(time.RFC3339)}
}

func (c Checker) Ready(ctx context.Context) (Result, bool) {
	timeout := c.Timeout
	if timeout <= 0 {
		timeout = 2 * time.Second
	}
	checkCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	checks := map[string]bool{
		"db":        true,
		"qdrant":    true,
		"embedding": c.EmbeddingOK,
	}
	if c.PingDB != nil {
		checks["db"] = c.PingDB(checkCtx) == nil
	}
	if c.QdrantOK != nil {
		checks["qdrant"] = c.QdrantOK(checkCtx)
	}
	ready := checks["db"] && checks["qdrant"] && checks["embedding"]
	status := "ready"
	if !ready {
		status = "not_ready"
	}
	return Result{
		Status:  status,
		Version: c.version(),
		Time:    c.now().Format(time.RFC3339),
		Checks:  checks,
	}, ready
}
