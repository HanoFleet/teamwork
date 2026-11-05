package grading

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"strings"
	"time"

	"campusclaw/internal/config"
	"campusclaw/internal/queue"

	"github.com/oklog/ulid/v2"
)

type Store struct {
	db  *sql.DB
	cfg config.Config
}

func NewStore(db *sql.DB, cfg config.Config) *Store {
	return &Store{db: db, cfg: cfg}
}

func (s *Store) ListPublished(ctx context.Context, classID int64) ([]Assignment, error) {
	rows, err := s.db.QueryContext(ctx, `
		SELECT id, class_id, title, published, COALESCE(created_at, UTC_TIMESTAMP())
		FROM assignments
		WHERE class_id=? AND published=1
		ORDER BY id ASC`, classID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	list := []Assignment{}
	for rows.Next() {
		var a Assignment
		if err := rows.Scan(&a.ID, &a.ClassID, &a.Title, &a.Published, &a.CreatedAt); err != nil {
			return nil, err
		}
		list = append(list, a)
	}
	return list, rows.Err()
}

func (s *Store) GetAssignment(ctx context.Context, id int64) (Assignment, error) {
	var a Assignment
	err := s.db.QueryRowContext(ctx, `
		SELECT id, class_id, title, published, COALESCE(created_at, UTC_TIMESTAMP())
		FROM assignments WHERE id=?`, id).Scan(&a.ID, &a.ClassID, &a.Title, &a.Published, &a.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Assignment{}, ErrNotFound
	}
	return a, err
}

func (s *Store) GetSubmission(ctx context.Context, id int64) (Submission, error) {
	var row Submission
	err := s.db.QueryRowContext(ctx, `
		SELECT id, assignment_id, student_id, class_id, body, version, status, created_at, updated_at
		FROM submissions WHERE id=?`, id).Scan(
		&row.ID, &row.AssignmentID, &row.StudentID, &row.ClassID, &row.Body, &row.Version, &row.Status, &row.CreatedAt, &row.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Submission{}, ErrNotFound
	}
	return row, err
}

func (s *Store) Submit(ctx context.Context, assignment Assignment, studentID int64, body string) (Submission, bool, error) {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return Submission{}, false, err
	}
	defer func() { _ = tx.Rollback() }()

	var current Submission
	err = tx.QueryRowContext(ctx, `
		SELECT id, assignment_id, student_id, class_id, body, version, status, created_at, updated_at
		FROM submissions
		WHERE assignment_id=? AND student_id=?
		ORDER BY version DESC LIMIT 1
		FOR UPDATE`, assignment.ID, studentID).Scan(
		&current.ID, &current.AssignmentID, &current.StudentID, &current.ClassID, &current.Body, &current.Version, &current.Status, &current.CreatedAt, &current.UpdatedAt)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return Submission{}, false, err
	}
	if err == nil && current.Body == body {
		if err := tx.Commit(); err != nil {
			return Submission{}, false, err
		}
		return current, false, nil
	}
	version := 1
	if err == nil {
		version = current.Version + 1
	}
	res, err := tx.ExecContext(ctx, `
		INSERT INTO submissions (assignment_id, student_id, class_id, body, version, status, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, 'submitted', UTC_TIMESTAMP(), UTC_TIMESTAMP())`,
		assignment.ID, studentID, assignment.ClassID, body, version)
	if err != nil {
		return Submission{}, false, err
	}
	id, err := res.LastInsertId()
	if err != nil {
		return Submission{}, false, err
	}
	if err := tx.Commit(); err != nil {
		return Submission{}, false, err
	}
	row, err := s.GetSubmission(ctx, id)
	return row, true, err
}

func (s *Store) EnqueueGrade(ctx context.Context, sub Submission) (Task, *Result, bool, error) {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return Task{}, nil, false, err
	}
	defer func() { _ = tx.Rollback() }()

	var locked Submission
	if err := tx.QueryRowContext(ctx, `
		SELECT id, assignment_id, student_id, class_id, body, version, status, created_at, updated_at
		FROM submissions WHERE id=? FOR UPDATE`, sub.ID).Scan(
		&locked.ID, &locked.AssignmentID, &locked.StudentID, &locked.ClassID, &locked.Body, &locked.Version, &locked.Status, &locked.CreatedAt, &locked.UpdatedAt); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Task{}, nil, false, ErrNotFound
		}
		return Task{}, nil, false, err
	}

	key := IdempotencyKey(locked.ID, locked.Version)
	var existing Result
	err = tx.QueryRowContext(ctx, `
		SELECT submission_id, version, score, feedback, task_id, graded_at
		FROM grade_results WHERE submission_id=? AND version=?`, locked.ID, locked.Version).Scan(
		&existing.SubmissionID, &existing.Version, &existing.Score, &existing.Feedback, &existing.TaskID, &existing.GradedAt)
	if err == nil {
		var task Task
		if err := scanTask(tx.QueryRowContext(ctx, taskSelect+" WHERE idempotency_key=?", key), &task); err != nil && !errors.Is(err, sql.ErrNoRows) {
			return Task{}, nil, false, err
		}
		if err := tx.Commit(); err != nil {
			return Task{}, nil, false, err
		}
		return task, &existing, false, nil
	}
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return Task{}, nil, false, err
	}

	var task Task
	err = scanTask(tx.QueryRowContext(ctx, taskSelect+" WHERE idempotency_key=?", key), &task)
	if err == nil {
		if err := tx.Commit(); err != nil {
			return Task{}, nil, false, err
		}
		return task, nil, false, nil
	}
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return Task{}, nil, false, err
	}

	taskID := ulid.Make().String()
	messageID := ulid.Make().String()
	payload, err := json.Marshal(queue.Payload{
		TaskID:            taskID,
		SubmissionID:      locked.ID,
		SubmissionVersion: locked.Version,
	})
	if err != nil {
		return Task{}, nil, false, err
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO grade_tasks (
			task_id, submission_id, submission_version, class_id, student_id,
			status, attempts, max_attempts, idempotency_key, created_at, updated_at
		) VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?, UTC_TIMESTAMP(), UTC_TIMESTAMP())`,
		taskID, locked.ID, locked.Version, locked.ClassID, locked.StudentID, s.cfg.GradeMaxAttempts, key); err != nil {
		return Task{}, nil, false, err
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO outbox_messages (
			message_id, idempotency_key, topic, payload, status, attempts, created_at
		) VALUES (?, ?, ?, ?, 'pending', 0, UTC_TIMESTAMP())`,
		messageID, key, s.cfg.QueueGrade, payload); err != nil {
		return Task{}, nil, false, err
	}
	if err := tx.Commit(); err != nil {
		return Task{}, nil, false, err
	}
	created, err := s.GetTaskByKey(ctx, key)
	return created, nil, true, err
}

const taskSelect = `SELECT id, task_id, submission_id, submission_version, class_id, student_id,
	status, attempts, max_attempts, idempotency_key, COALESCE(error,''), next_run_at, started_at, finished_at, created_at, updated_at
	FROM grade_tasks`

func scanTask(row interface{ Scan(dest ...any) error }, task *Task) error {
	var errText string
	var next, started, finished sql.NullTime
	if err := row.Scan(&task.ID, &task.TaskID, &task.SubmissionID, &task.SubmissionVersion, &task.ClassID, &task.StudentID,
		&task.Status, &task.Attempts, &task.MaxAttempts, &task.IdempotencyKey, &errText, &next, &started, &finished, &task.CreatedAt, &task.UpdatedAt); err != nil {
		return err
	}
	task.Error = errText
	if next.Valid {
		task.NextRunAt = &next.Time
	}
	if started.Valid {
		task.StartedAt = &started.Time
	}
	if finished.Valid {
		task.FinishedAt = &finished.Time
	}
	return nil
}

func (s *Store) GetTaskByID(ctx context.Context, taskID string) (Task, error) {
	var task Task
	err := scanTask(s.db.QueryRowContext(ctx, taskSelect+" WHERE task_id=?", taskID), &task)
	if errors.Is(err, sql.ErrNoRows) {
		return Task{}, ErrNotFound
	}
	return task, err
}

func (s *Store) GetTaskByKey(ctx context.Context, key string) (Task, error) {
	var task Task
	err := scanTask(s.db.QueryRowContext(ctx, taskSelect+" WHERE idempotency_key=?", key), &task)
	if errors.Is(err, sql.ErrNoRows) {
		return Task{}, ErrNotFound
	}
	return task, err
}

func (s *Store) GetResult(ctx context.Context, submissionID int64, version int) (Result, error) {
	var row Result
	err := s.db.QueryRowContext(ctx, `
		SELECT submission_id, version, score, feedback, task_id, graded_at
		FROM grade_results WHERE submission_id=? AND version=?`, submissionID, version).Scan(
		&row.SubmissionID, &row.Version, &row.Score, &row.Feedback, &row.TaskID, &row.GradedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Result{}, ErrNotFound
	}
	return row, err
}

func (s *Store) GetSubmissionVersion(ctx context.Context, submissionID int64, version int) (Submission, error) {
	var row Submission
	err := s.db.QueryRowContext(ctx, `
		SELECT id, assignment_id, student_id, class_id, body, version, status, created_at, updated_at
		FROM submissions WHERE id=? AND version=?`, submissionID, version).Scan(
		&row.ID, &row.AssignmentID, &row.StudentID, &row.ClassID, &row.Body, &row.Version, &row.Status, &row.CreatedAt, &row.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Submission{}, ErrNotFound
	}
	return row, err
}

func (s *Store) MarkRunning(ctx context.Context, task Task) (Task, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return Task{}, err
	}
	defer func() { _ = tx.Rollback() }()
	var current Task
	if err := scanTask(tx.QueryRowContext(ctx, taskSelect+" WHERE task_id=? FOR UPDATE", task.TaskID), &current); err != nil {
		return Task{}, err
	}
	if IsTerminal(current.Status) {
		if err := tx.Commit(); err != nil {
			return Task{}, err
		}
		return current, nil
	}
	if _, err := OnStart(current.Status); err != nil {
		return Task{}, err
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE grade_tasks SET status='running', attempts=attempts+1, started_at=UTC_TIMESTAMP(), updated_at=UTC_TIMESTAMP(), error=NULL
		WHERE task_id=?`, current.TaskID); err != nil {
		return Task{}, err
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE submissions SET status='grading', updated_at=UTC_TIMESTAMP() WHERE id=?`, current.SubmissionID); err != nil {
		return Task{}, err
	}
	if err := tx.Commit(); err != nil {
		return Task{}, err
	}
	return s.GetTaskByID(ctx, current.TaskID)
}

func (s *Store) MarkSucceeded(ctx context.Context, task Task, score ScoreResult) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	key := IdempotencyKey(task.SubmissionID, task.SubmissionVersion)
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO grade_results (submission_id, version, idempotency_key, score, feedback, task_id, graded_at)
		VALUES (?, ?, ?, ?, ?, ?, UTC_TIMESTAMP())
		ON DUPLICATE KEY UPDATE id=id`,
		task.SubmissionID, task.SubmissionVersion, key, score.Score, score.Feedback, task.TaskID); err != nil {
		return err
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE grade_tasks SET status='succeeded', error=NULL, finished_at=UTC_TIMESTAMP(), updated_at=UTC_TIMESTAMP()
		WHERE task_id=?`, task.TaskID); err != nil {
		return err
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE submissions SET status='graded', updated_at=UTC_TIMESTAMP() WHERE id=?`, task.SubmissionID); err != nil {
		return err
	}
	return tx.Commit()
}

func (s *Store) MarkFailure(ctx context.Context, task Task, nextStatus, message string, retryIn time.Duration) error {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	msg := strings.TrimSpace(message)
	if len(msg) > 512 {
		msg = msg[:512]
	}
	if nextStatus == StatusPending {
		if _, err := tx.ExecContext(ctx, `
			UPDATE grade_tasks
			SET status='pending', error=?, next_run_at=DATE_ADD(UTC_TIMESTAMP(), INTERVAL ? MICROSECOND), updated_at=UTC_TIMESTAMP(), finished_at=NULL
			WHERE task_id=?`, msg, retryIn.Microseconds(), task.TaskID); err != nil {
			return err
		}
	} else {
		if _, err := tx.ExecContext(ctx, `
			UPDATE grade_tasks
			SET status=?, error=?, finished_at=UTC_TIMESTAMP(), next_run_at=NULL, updated_at=UTC_TIMESTAMP()
			WHERE task_id=?`, nextStatus, msg, task.TaskID); err != nil {
			return err
		}
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE submissions SET status='submitted', updated_at=UTC_TIMESTAMP() WHERE id=?`, task.SubmissionID); err != nil {
		return err
	}
	return tx.Commit()
}
