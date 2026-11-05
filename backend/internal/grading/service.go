package grading

import (
	"context"
	"errors"
	"strings"
	"unicode/utf8"

	"campusclaw/internal/config"
	"database/sql"
)

type Actor struct {
	ID      int64
	Role    string
	ClassID int64
}

type Service struct {
	store *Store
}

func NewService(db *sql.DB, cfg config.Config) *Service {
	return &Service{store: NewStore(db, cfg)}
}

func (s *Service) Store() *Store { return s.store }

func (s *Service) ListAssignments(ctx context.Context, actor Actor) ([]Assignment, error) {
	return s.store.ListPublished(ctx, actor.ClassID)
}

func (s *Service) Submit(ctx context.Context, actor Actor, assignmentID int64, body string) (Submission, bool, error) {
	if actor.Role != "student" {
		return Submission{}, false, ErrForbidden
	}
	trimmed := strings.TrimSpace(body)
	n := utf8.RuneCountInString(trimmed)
	if n < 1 || n > 20000 {
		return Submission{}, false, ErrInvalid
	}
	asg, err := s.store.GetAssignment(ctx, assignmentID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return Submission{}, false, ErrNotFound
		}
		return Submission{}, false, ErrUnavailable
	}
	if asg.ClassID != actor.ClassID || !asg.Published {
		return Submission{}, false, ErrNotFound
	}
	row, created, err := s.store.Submit(ctx, asg, actor.ID, trimmed)
	if err != nil {
		return Submission{}, false, ErrUnavailable
	}
	return row, created, nil
}

func (s *Service) EnqueueGrade(ctx context.Context, actor Actor, submissionID int64) (Task, *Result, bool, error) {
	sub, err := s.store.GetSubmission(ctx, submissionID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return Task{}, nil, false, ErrNotFound
		}
		return Task{}, nil, false, ErrUnavailable
	}
	if sub.StudentID != actor.ID || sub.ClassID != actor.ClassID {
		return Task{}, nil, false, ErrNotFound
	}
	task, result, created, err := s.store.EnqueueGrade(ctx, sub)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return Task{}, nil, false, ErrNotFound
		}
		return Task{}, nil, false, ErrUnavailable
	}
	return task, result, created, nil
}

func (s *Service) GetTask(ctx context.Context, actor Actor, taskID string) (Task, *Result, error) {
	if taskID == "" || len(taskID) != 26 {
		return Task{}, nil, ErrNotFound
	}
	task, err := s.store.GetTaskByID(ctx, taskID)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return Task{}, nil, ErrNotFound
		}
		return Task{}, nil, ErrUnavailable
	}
	if task.ClassID != actor.ClassID {
		return Task{}, nil, ErrNotFound
	}
	if actor.Role != "teacher" && task.StudentID != actor.ID {
		return Task{}, nil, ErrNotFound
	}
	result, err := s.store.GetResult(ctx, task.SubmissionID, task.SubmissionVersion)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			return task, nil, nil
		}
		return Task{}, nil, ErrUnavailable
	}
	return task, &result, nil
}
