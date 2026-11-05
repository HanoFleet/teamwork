package outbox

import (
	"context"
	"database/sql"
	"encoding/json"
	"log/slog"
	"time"

	"campusclaw/internal/config"
	"campusclaw/internal/grading"
	"campusclaw/internal/queue"
)

type Dispatcher struct {
	db     *sql.DB
	broker *queue.Broker
	cfg    config.Config
	logger *slog.Logger
}

func New(db *sql.DB, broker *queue.Broker, cfg config.Config, logger *slog.Logger) *Dispatcher {
	return &Dispatcher{db: db, broker: broker, cfg: cfg, logger: logger}
}

func (d *Dispatcher) Run(ctx context.Context) {
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := d.flush(ctx); err != nil && d.logger != nil {
				d.logger.Warn("outbox_flush", "event", "outbox", "reason", err.Error())
			}
		}
	}
}

func (d *Dispatcher) flush(ctx context.Context) error {
	if d.broker == nil {
		return nil
	}
	tx, err := d.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	rows, err := tx.QueryContext(ctx, `
		SELECT id, payload, attempts
		FROM outbox_messages
		WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at <= UTC_TIMESTAMP())
		ORDER BY id
		LIMIT 20
		FOR UPDATE SKIP LOCKED`)
	if err != nil {
		return err
	}
	type item struct {
		id       int64
		payload  []byte
		attempts int
	}
	var batch []item
	for rows.Next() {
		var row item
		if err := rows.Scan(&row.id, &row.payload, &row.attempts); err != nil {
			_ = rows.Close()
			return err
		}
		batch = append(batch, row)
	}
	if err := rows.Close(); err != nil {
		return err
	}
	if err := rows.Err(); err != nil {
		return err
	}
	for _, row := range batch {
		var payload queue.Payload
		if err := json.Unmarshal(row.payload, &payload); err != nil {
			return err
		}
		pubCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
		pubErr := d.broker.Ensure(pubCtx)
		if pubErr == nil {
			pubErr = d.broker.Publish(pubCtx, queue.KeyTasks, payload)
		}
		cancel()
		if pubErr != nil {
			sec := grading.RetrySecondsForAttempt(row.attempts + 1)
			if _, err := tx.ExecContext(ctx, `
				UPDATE outbox_messages
				SET attempts=attempts+1, next_attempt_at=DATE_ADD(UTC_TIMESTAMP(), INTERVAL ? SECOND)
				WHERE id=? AND status='pending'`, sec, row.id); err != nil {
				return err
			}
			if d.logger != nil {
				d.logger.Warn("outbox_publish", "event", "outbox", "reason", pubErr.Error())
			}
			continue
		}
		if _, err := tx.ExecContext(ctx, `
			UPDATE outbox_messages
			SET status='published', published_at=UTC_TIMESTAMP(), attempts=attempts+1
			WHERE id=? AND status='pending'`, row.id); err != nil {
			return err
		}
	}
	return tx.Commit()
}
