// Package audit stores security-relevant events in audit_logs.
package audit

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

const (
	StatusSuccess  = "success"
	StatusFailure  = "failure"
	StatusDenied   = "denied"
	StatusAccepted = "accepted"
)

type Entry struct {
	ID               int64          `json:"id"`
	OccurredAt       time.Time      `json:"occurred_at"`
	OperatorID       int64          `json:"operator_id,omitempty"`
	OperatorUsername string         `json:"operator_username"`
	OperatorRole     string         `json:"operator_role"`
	ClassID          int64          `json:"class_id,omitempty"`
	Operation        string         `json:"operation"`
	ObjectType       string         `json:"object_type"`
	ObjectID         string         `json:"object_id"`
	ResultStatus     string         `json:"result_status"`
	SkillKey         string         `json:"skill_key,omitempty"`
	DurationMS       *int           `json:"duration_ms,omitempty"`
	Usage            map[string]any `json:"usage,omitempty"`
	ErrorCode        string         `json:"error_code,omitempty"`
	RequestID        string         `json:"request_id,omitempty"`
}

type Filter struct {
	OperatorID int64
	ClassID    int64
	SkillKey   string
	From       time.Time
	To         time.Time
	Limit      int
}

type Store struct {
	db *sql.DB
}

func NewStore(db *sql.DB) *Store { return &Store{db: db} }

func (s *Store) Append(ctx context.Context, e Entry) error {
	username := truncate(strings.TrimSpace(e.OperatorUsername), 64)
	if username == "" {
		username = "anonymous"
	}
	role := e.OperatorRole
	if role != "teacher" && role != "student" && role != "system" {
		role = "system"
	}
	status := e.ResultStatus
	if status != StatusSuccess && status != StatusFailure && status != StatusDenied && status != StatusAccepted {
		status = StatusFailure
	}
	operation := truncate(strings.TrimSpace(e.Operation), 64)
	objectType := truncate(strings.TrimSpace(e.ObjectType), 32)
	objectID := truncate(strings.TrimSpace(e.ObjectID), 64)
	skillKey := truncate(strings.TrimSpace(e.SkillKey), 64)
	errorCode := truncate(strings.TrimSpace(e.ErrorCode), 64)
	requestID := truncate(strings.TrimSpace(e.RequestID), 64)
	usage, err := marshalUsage(e.Usage)
	if err != nil {
		return err
	}
	occurred := e.OccurredAt
	if occurred.IsZero() {
		occurred = time.Now().UTC()
	}
	var operatorID, classID any
	if e.OperatorID > 0 {
		operatorID = e.OperatorID
	}
	if e.ClassID > 0 {
		classID = e.ClassID
	}
	var duration any
	if e.DurationMS != nil {
		duration = *e.DurationMS
	}
	_, err = s.db.ExecContext(ctx, `
		INSERT INTO audit_logs (
			occurred_at, operator_id, operator_username, operator_role, class_id,
			operation, object_type, object_id, result_status, skill_key,
			duration_ms, usage_json, error_code, request_id
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		occurred.UTC(), operatorID, username, role, classID,
		operation, objectType, objectID, status, nullString(skillKey),
		duration, usage, nullString(errorCode), nullString(requestID))
	return err
}

func (s *Store) List(ctx context.Context, f Filter) ([]Entry, error) {
	if f.Limit <= 0 {
		f.Limit = 100
	}
	if f.Limit > 100 {
		f.Limit = 100
	}
	query := `SELECT id, occurred_at, operator_id, operator_username, operator_role, class_id,
		operation, object_type, object_id, result_status, skill_key,
		duration_ms, usage_json, error_code, request_id
		FROM audit_logs WHERE class_id=?`
	args := []any{f.ClassID}
	if f.OperatorID > 0 {
		query += ` AND operator_id=?`
		args = append(args, f.OperatorID)
	}
	if f.SkillKey != "" {
		query += ` AND skill_key=?`
		args = append(args, f.SkillKey)
	}
	if !f.From.IsZero() {
		query += ` AND occurred_at>=?`
		args = append(args, f.From.UTC())
	}
	if !f.To.IsZero() {
		query += ` AND occurred_at<=?`
		args = append(args, f.To.UTC())
	}
	query += ` ORDER BY occurred_at DESC, id DESC LIMIT ?`
	args = append(args, f.Limit)
	rows, err := s.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	list := []Entry{}
	for rows.Next() {
		var e Entry
		var operatorID, classID, duration sql.NullInt64
		var skillKey, errorCode, requestID sql.NullString
		var usage []byte
		if err := rows.Scan(&e.ID, &e.OccurredAt, &operatorID, &e.OperatorUsername, &e.OperatorRole, &classID,
			&e.Operation, &e.ObjectType, &e.ObjectID, &e.ResultStatus, &skillKey,
			&duration, &usage, &errorCode, &requestID); err != nil {
			return nil, err
		}
		if operatorID.Valid {
			e.OperatorID = operatorID.Int64
		}
		if classID.Valid {
			e.ClassID = classID.Int64
		}
		if duration.Valid {
			v := int(duration.Int64)
			e.DurationMS = &v
		}
		e.SkillKey = skillKey.String
		e.ErrorCode = errorCode.String
		e.RequestID = requestID.String
		if len(usage) > 0 {
			if err := json.Unmarshal(usage, &e.Usage); err != nil {
				e.Usage = map[string]any{"invalid": true}
			}
		}
		list = append(list, e)
	}
	return list, rows.Err()
}

func marshalUsage(usage map[string]any) (any, error) {
	if usage == nil {
		return nil, nil
	}
	raw, err := json.Marshal(usage)
	if err != nil {
		return nil, fmt.Errorf("audit usage: %w", err)
	}
	if len(raw) > 2048 {
		return nil, errors.New("audit usage too large")
	}
	return raw, nil
}

func nullString(v string) any {
	if v == "" {
		return nil
	}
	return v
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
