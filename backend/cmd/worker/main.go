package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"
	"time"

	"campusclaw/internal/config"
	"campusclaw/internal/db"
	"campusclaw/internal/grading"
	"campusclaw/internal/logging"
	"campusclaw/internal/queue"
	"campusclaw/internal/worker"
)

func main() {
	logger := logging.New()
	if err := run(logger); err != nil {
		logger.Error("worker_failed", "event", "failure", "reason", err.Error())
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
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

	broker := queue.New(cfg.RabbitMQURL)
	defer broker.Close()
	store := grading.NewStore(conn, cfg)
	w := worker.New(store, broker, cfg, logger)

	signalCtx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	logger.Info("worker_startup", "event", "startup", "version", cfg.AppVersion)
	err = w.Run(signalCtx)
	logger.Info("worker_shutdown", "event", "shutdown")
	if err != nil && signalCtx.Err() == nil {
		return err
	}
	return nil
}
