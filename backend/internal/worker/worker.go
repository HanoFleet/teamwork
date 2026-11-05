package worker

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"math/rand"
	"time"

	"campusclaw/internal/config"
	"campusclaw/internal/grading"
	"campusclaw/internal/queue"

	amqp "github.com/rabbitmq/amqp091-go"
)

type Worker struct {
	store  *grading.Store
	broker *queue.Broker
	cfg    config.Config
	logger *slog.Logger
}

func New(store *grading.Store, broker *queue.Broker, cfg config.Config, logger *slog.Logger) *Worker {
	return &Worker{store: store, broker: broker, cfg: cfg, logger: logger}
}

func (w *Worker) Run(ctx context.Context) error {
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		msgs, err := w.broker.Consume(ctx, w.cfg.QueueGrade)
		if err != nil {
			w.log("worker_connect", map[string]any{"reason": err.Error()})
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(2 * time.Second):
			}
			continue
		}
		w.log("worker_consume", map[string]any{"queue": w.cfg.QueueGrade})
	consume:
		for {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case msg, ok := <-msgs:
				if !ok {
					break consume
				}
				w.handle(ctx, msg)
			}
		}
	}
}

func (w *Worker) handle(ctx context.Context, msg amqp.Delivery) {
	started := time.Now()
	var payload queue.Payload
	if err := json.Unmarshal(msg.Body, &payload); err != nil {
		w.log("worker_invalid_payload", map[string]any{"reason": err.Error()})
		_ = msg.Ack(false)
		return
	}
	task, err := w.store.GetTaskByID(ctx, payload.TaskID)
	if err != nil {
		if errors.Is(err, grading.ErrNotFound) {
			_ = msg.Ack(false)
			return
		}
		w.log("worker_load_task", map[string]any{"task_id": payload.TaskID, "reason": err.Error()})
		_ = msg.Nack(false, true)
		return
	}
	fields := map[string]any{
		"task_id":       task.TaskID,
		"submission_id": task.SubmissionID,
		"student_id":    task.StudentID,
		"status":        task.Status,
		"attempts":      task.Attempts,
	}
	if grading.IsTerminal(task.Status) {
		_ = msg.Ack(false)
		w.log("worker_skip_terminal", fields)
		return
	}
	if _, err := w.store.GetResult(ctx, task.SubmissionID, task.SubmissionVersion); err == nil {
		_ = w.store.MarkSucceeded(ctx, task, grading.ScoreResult{})
		_ = msg.Ack(false)
		w.log("worker_result_exists", fields)
		return
	}

	running, err := w.store.MarkRunning(ctx, task)
	if err != nil {
		w.log("worker_mark_running", map[string]any{"task_id": task.TaskID, "reason": err.Error()})
		_ = msg.Nack(false, true)
		return
	}
	if grading.IsTerminal(running.Status) {
		_ = msg.Ack(false)
		return
	}
	sub, err := w.store.GetSubmissionVersion(ctx, running.SubmissionID, running.SubmissionVersion)
	if err != nil {
		w.fail(ctx, msg, running, err, !errors.Is(err, grading.ErrNotFound), started)
		return
	}
	scoreCtx, cancel := context.WithTimeout(ctx, w.cfg.GradeModelTimeout+w.cfg.GradeLocalDelay+time.Second)
	score, scoreErr := grading.Score(scoreCtx, w.cfg, sub.Body)
	cancel()
	if scoreErr != nil {
		transient := errors.Is(scoreErr, grading.ErrTransient)
		w.fail(ctx, msg, running, scoreErr, transient, started)
		return
	}
	if err := w.store.MarkSucceeded(ctx, running, score); err != nil {
		w.log("worker_mark_succeeded", map[string]any{"task_id": running.TaskID, "reason": err.Error()})
		_ = msg.Nack(false, true)
		return
	}
	fields["status"] = grading.StatusSucceeded
	fields["attempts"] = running.Attempts
	fields["duration_ms"] = time.Since(started).Milliseconds()
	w.log("worker_succeeded", fields)
	_ = msg.Ack(false)
}

func (w *Worker) fail(ctx context.Context, msg amqp.Delivery, task grading.Task, cause error, transient bool, started time.Time) {
	next, err := grading.OnFailure(grading.StatusRunning, task.Attempts, task.MaxAttempts, transient)
	if err != nil {
		next = grading.StatusFailed
	}
	retry := time.Duration(grading.RetrySecondsForAttempt(task.Attempts)) * time.Second
	jitter := time.Duration(0)
	if w.cfg.GradeJitter > 0 {
		maxMS := int(w.cfg.GradeJitter / time.Millisecond)
		if maxMS > 0 {
			jitter = time.Duration(rand.Intn(maxMS+1)) * time.Millisecond
		}
	}
	if err := w.store.MarkFailure(ctx, task, next, cause.Error(), retry+jitter); err != nil {
		w.log("worker_mark_failure", map[string]any{"task_id": task.TaskID, "reason": err.Error()})
		_ = msg.Nack(false, true)
		return
	}
	payload := queue.Payload{
		TaskID:            task.TaskID,
		SubmissionID:      task.SubmissionID,
		SubmissionVersion: task.SubmissionVersion,
		Error:             cause.Error(),
	}
	switch next {
	case grading.StatusPending:
		key := queue.RetryRoutingKey(grading.RetrySecondsForAttempt(task.Attempts))
		if err := w.broker.Publish(ctx, key, payload); err != nil {
			w.log("worker_retry_publish", map[string]any{"task_id": task.TaskID, "reason": err.Error()})
		}
	case grading.StatusFailed, grading.StatusDead:
		if err := w.broker.Publish(ctx, queue.KeyDead, payload); err != nil {
			w.log("worker_dead_publish", map[string]any{"task_id": task.TaskID, "reason": err.Error()})
		}
	}
	w.log("worker_failed", map[string]any{
		"task_id":       task.TaskID,
		"submission_id": task.SubmissionID,
		"student_id":    task.StudentID,
		"status":        next,
		"attempts":      task.Attempts,
		"duration_ms":   time.Since(started).Milliseconds(),
	})
	_ = msg.Ack(false)
}

func (w *Worker) log(msg string, fields map[string]any) {
	if w.logger == nil {
		return
	}
	args := make([]any, 0, len(fields)*2)
	for k, v := range fields {
		args = append(args, k, v)
	}
	w.logger.Info(msg, args...)
}
