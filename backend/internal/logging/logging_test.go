package logging

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestValidRequestID(t *testing.T) {
	cases := map[string]bool{
		"abc12345":  true,
		"a_b-c123":  true,
		"short":     false,
		"has space": false,
		"":          false,
	}
	for id, want := range cases {
		if got := ValidRequestID(id); got != want {
			t.Fatalf("ValidRequestID(%q) = %v, want %v", id, got, want)
		}
	}
}

func TestMiddlewareGeneratesAndEchoesRequestID(t *testing.T) {
	var buf bytes.Buffer
	logger := slog.New(slog.NewJSONHandler(&buf, nil))
	h := Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusTeapot)
	}), logger)

	req := httptest.NewRequest(http.MethodGet, "/api/me?x=1", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	id := rec.Header().Get(Header)
	if !ValidRequestID(id) {
		t.Fatalf("response request id = %q", id)
	}
	if rec.Code != http.StatusTeapot {
		t.Fatalf("status = %d", rec.Code)
	}
	var line map[string]any
	if err := json.Unmarshal(bytes.TrimSpace(buf.Bytes()), &line); err != nil {
		t.Fatalf("log is not JSON: %v (%s)", err, buf.String())
	}
	if line["request_id"] != id {
		t.Fatalf("log request_id = %v, header = %s", line["request_id"], id)
	}
	if line["path"] != "/api/me" {
		t.Fatalf("log path = %v", line["path"])
	}
	if _, ok := line["duration_ms"]; !ok {
		t.Fatal("log missing duration_ms")
	}
}

func TestMiddlewareKeepsValidRequestID(t *testing.T) {
	var buf bytes.Buffer
	logger := slog.New(slog.NewJSONHandler(&buf, nil))
	h := Middleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}), logger)

	req := httptest.NewRequest(http.MethodGet, "/live", nil)
	req.Header.Set(Header, "verify-lesson07")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	if got := rec.Header().Get(Header); got != "verify-lesson07" {
		t.Fatalf("request id = %q", got)
	}
}
