package grading

import (
	"errors"
	"fmt"
	"time"
)

var (
	ErrNotFound     = errors.New("not_found")
	ErrForbidden    = errors.New("forbidden")
	ErrInvalid      = errors.New("invalid_request")
	ErrUnavailable  = errors.New("unavailable")
	ErrTransient    = errors.New("transient")
	ErrPermanent    = errors.New("permanent")
	ErrIllegalState = errors.New("illegal_state")
)

const (
	SubSubmitted = "submitted"
	SubGrading   = "grading"
	SubGraded    = "graded"

	StatusPending   = "pending"
	StatusRunning   = "running"
	StatusSucceeded = "succeeded"
	StatusFailed    = "failed"
	StatusDead      = "dead"

	TaskTypeGrade = "grade"
)

type Assignment struct {
	ID        int64
	ClassID   int64
	Title     string
	Published bool
	CreatedAt time.Time
}

type Submission struct {
	ID           int64
	AssignmentID int64
	StudentID    int64
	ClassID      int64
	Body         string
	Version      int
	Status       string
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

type Task struct {
	ID                int64
	TaskID            string
	SubmissionID      int64
	SubmissionVersion int
	ClassID           int64
	StudentID         int64
	Status            string
	Attempts          int
	MaxAttempts       int
	IdempotencyKey    string
	Error             string
	NextRunAt         *time.Time
	StartedAt         *time.Time
	FinishedAt        *time.Time
	CreatedAt         time.Time
	UpdatedAt         time.Time
}

type Result struct {
	SubmissionID int64
	Version      int
	Score        float64
	Feedback     string
	TaskID       string
	GradedAt     time.Time
}

func IdempotencyKey(submissionID int64, version int) string {
	return fmt.Sprintf("grade:%d:%d", submissionID, version)
}
