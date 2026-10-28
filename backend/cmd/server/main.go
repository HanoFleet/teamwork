package main

import (
	"context"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"campusclaw/internal/auth"
	"campusclaw/internal/config"
	"campusclaw/internal/db"
	"campusclaw/internal/httpapi"
	"campusclaw/internal/lifecycle"
	"campusclaw/internal/logging"
)

func main() {
	logger := logging.New()
	if err := run(logger); err != nil {
		logger.Error("startup_or_shutdown_failed", "event", "failure", "reason", err.Error())
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(cfg.UploadDir, 0o750); err != nil {
		return err
	}
	conn, err := db.Open(cfg)
	if err != nil {
		return err
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Minute)
	defer cancel()
	if err := db.Wait(ctx, conn); err != nil {
		return err
	}
	if err := db.Migrate(ctx, conn); err != nil {
		return err
	}
	if err := db.Seed(ctx, conn, cfg); err != nil {
		return err
	}
	auth.DummyHash()

	api := httpapi.New(cfg, conn, logger)
	if err := backfillIndex(ctx, api, logger); err != nil {
		logger.Warn("knowledge_index_backfill", "event", "backfill", "reason", err.Error())
	}

	listener, err := net.Listen("tcp", cfg.APIAddr)
	if err != nil {
		return err
	}
	signalCtx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	srv := &http.Server{
		Handler:           api.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       30 * time.Second,
	}
	logger.Info("startup", "event", "startup", "version", cfg.AppVersion, "addr", cfg.APIAddr)
	if err := lifecycle.Serve(signalCtx, srv, listener, cfg.ShutdownTimeout, logger); err != nil {
		return err
	}
	logger.Info("shutdown_complete", "event", "shutdown")
	return nil
}

func backfillIndex(ctx context.Context, api *httpapi.Server, logger *slog.Logger) error {
	var last error
	for i := 0; i < 20; i++ {
		last = api.Backfill(ctx)
		if last == nil {
			return nil
		}
		logger.Warn("knowledge_index_wait", "event", "backfill", "attempt", i+1, "reason", last.Error())
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(2 * time.Second):
		}
	}
	return last
}
