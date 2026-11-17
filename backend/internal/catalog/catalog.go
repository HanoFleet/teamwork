// Package catalog owns skill and assistant configuration queries.
package catalog

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

var ErrNotFound = errors.New("not_found")

type Skill struct {
	ID          int64     `json:"id"`
	Key         string    `json:"skill_key"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Enabled     bool      `json:"enabled"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type Assistant struct {
	ID           int64     `json:"id"`
	ClassID      int64     `json:"class_id"`
	Name         string    `json:"name"`
	SystemPrompt string    `json:"system_prompt"`
	Enabled      bool      `json:"enabled"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type SkillPatch struct {
	Name        *string
	Description *string
	Enabled     *bool
}

type AssistantPatch struct {
	Name         *string
	SystemPrompt *string
	Enabled      *bool
}

type Store struct{ db *sql.DB }

func NewStore(db *sql.DB) *Store { return &Store{db: db} }

func (s *Store) ListSkills(ctx context.Context) ([]Skill, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT id, COALESCE(skill_key,''), name, COALESCE(description,''), enabled, COALESCE(updated_at, UTC_TIMESTAMP())
		FROM skills ORDER BY id ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	list := []Skill{}
	for rows.Next() {
		var v Skill
		if err := rows.Scan(&v.ID, &v.Key, &v.Name, &v.Description, &v.Enabled, &v.UpdatedAt); err != nil {
			return nil, err
		}
		list = append(list, v)
	}
	return list, rows.Err()
}

func (s *Store) GetSkill(ctx context.Context, key string) (Skill, error) {
	var v Skill
	err := s.db.QueryRowContext(ctx, `SELECT id, COALESCE(skill_key,''), name, COALESCE(description,''), enabled, COALESCE(updated_at, UTC_TIMESTAMP())
		FROM skills WHERE skill_key=?`, key).Scan(&v.ID, &v.Key, &v.Name, &v.Description, &v.Enabled, &v.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Skill{}, ErrNotFound
	}
	return v, err
}

func (s *Store) UpdateSkill(ctx context.Context, key string, patch SkillPatch) (Skill, error) {
	if _, err := s.GetSkill(ctx, key); err != nil {
		return Skill{}, err
	}
	sets := []string{}
	args := []any{}
	if patch.Name != nil {
		sets = append(sets, "name=?")
		args = append(args, strings.TrimSpace(*patch.Name))
	}
	if patch.Description != nil {
		sets = append(sets, "description=?")
		args = append(args, strings.TrimSpace(*patch.Description))
	}
	if patch.Enabled != nil {
		sets = append(sets, "enabled=?")
		args = append(args, *patch.Enabled)
	}
	if len(sets) == 0 {
		return s.GetSkill(ctx, key)
	}
	sets = append(sets, "updated_at=UTC_TIMESTAMP()")
	args = append(args, key)
	if _, err := s.db.ExecContext(ctx, fmt.Sprintf("UPDATE skills SET %s WHERE skill_key=?", strings.Join(sets, ", ")), args...); err != nil {
		return Skill{}, err
	}
	return s.GetSkill(ctx, key)
}

func (s *Store) ListAssistants(ctx context.Context, classID int64) ([]Assistant, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT id, class_id, name, COALESCE(system_prompt,''), enabled, COALESCE(updated_at, UTC_TIMESTAMP())
		FROM assistants WHERE class_id=? ORDER BY id ASC`, classID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	list := []Assistant{}
	for rows.Next() {
		var v Assistant
		if err := rows.Scan(&v.ID, &v.ClassID, &v.Name, &v.SystemPrompt, &v.Enabled, &v.UpdatedAt); err != nil {
			return nil, err
		}
		list = append(list, v)
	}
	return list, rows.Err()
}

func (s *Store) GetAssistant(ctx context.Context, id, classID int64) (Assistant, error) {
	var v Assistant
	err := s.db.QueryRowContext(ctx, `SELECT id, class_id, name, COALESCE(system_prompt,''), enabled, COALESCE(updated_at, UTC_TIMESTAMP())
		FROM assistants WHERE id=? AND class_id=?`, id, classID).Scan(&v.ID, &v.ClassID, &v.Name, &v.SystemPrompt, &v.Enabled, &v.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Assistant{}, ErrNotFound
	}
	return v, err
}

func (s *Store) UpdateAssistant(ctx context.Context, id, classID int64, patch AssistantPatch) (Assistant, error) {
	if _, err := s.GetAssistant(ctx, id, classID); err != nil {
		return Assistant{}, err
	}
	sets := []string{}
	args := []any{}
	if patch.Name != nil {
		sets = append(sets, "name=?")
		args = append(args, strings.TrimSpace(*patch.Name))
	}
	if patch.SystemPrompt != nil {
		sets = append(sets, "system_prompt=?")
		args = append(args, strings.TrimSpace(*patch.SystemPrompt))
	}
	if patch.Enabled != nil {
		sets = append(sets, "enabled=?")
		args = append(args, *patch.Enabled)
	}
	if len(sets) == 0 {
		return s.GetAssistant(ctx, id, classID)
	}
	sets = append(sets, "updated_at=UTC_TIMESTAMP()")
	args = append(args, id, classID)
	if _, err := s.db.ExecContext(ctx, fmt.Sprintf("UPDATE assistants SET %s WHERE id=? AND class_id=?", strings.Join(sets, ", ")), args...); err != nil {
		return Assistant{}, err
	}
	return s.GetAssistant(ctx, id, classID)
}
