package httpapi

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"time"

	"campusclaw/internal/audit"
	"campusclaw/internal/catalog"
)

type skillPatchRequest struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
	Enabled     *bool   `json:"enabled"`
}

type assistantPatchRequest struct {
	Name         *string `json:"name"`
	SystemPrompt *string `json:"system_prompt"`
	Enabled      *bool   `json:"enabled"`
}

func (s *Server) listSkills(w http.ResponseWriter, r *http.Request) {
	if _, ok := s.requireUser(w, r); !ok {
		return
	}
	if s.catalog == nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	list, err := s.catalog.ListSkills(r.Context())
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"skills": list})
}

func (s *Server) patchSkill(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	key := strings.TrimSpace(r.PathValue("key"))
	object := "skill:" + key
	if u.Role != "teacher" {
		s.recordAudit(r, u, "config.change", "skill", object, audit.StatusDenied, key, nil, nil, "forbidden")
		writeError(w, http.StatusForbidden, "forbidden")
		return
	}
	var req skillPatchRequest
	if !decodeStrictJSON(w, r, &req) {
		return
	}
	if !validSkillPatch(w, req) {
		return
	}
	started := time.Now()
	updated, err := s.catalog.UpdateSkill(r.Context(), key, catalog.SkillPatch{
		Name: req.Name, Description: req.Description, Enabled: req.Enabled,
	})
	duration := int(time.Since(started).Milliseconds())
	if err != nil {
		if errors.Is(err, catalog.ErrNotFound) {
			s.recordAudit(r, u, "config.change", "skill", object, audit.StatusDenied, key, &duration, nil, "not_found")
			writeError(w, http.StatusNotFound, "not_found")
			return
		}
		s.recordAudit(r, u, "config.change", "skill", object, audit.StatusFailure, key, &duration, nil, "unavailable")
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	s.recordAudit(r, u, "config.change", "skill", object, audit.StatusSuccess, key, &duration, nil, "")
	writeJSON(w, http.StatusOK, updated)
}

func (s *Server) listAssistants(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	if s.catalog == nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	list, err := s.catalog.ListAssistants(r.Context(), u.ClassID)
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"assistants": list})
}

func (s *Server) patchAssistant(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	id, ok := parsePositiveID(r.PathValue("id"))
	if !ok {
		writeError(w, http.StatusNotFound, "not_found")
		return
	}
	object := "assistant:" + r.PathValue("id")
	if u.Role != "teacher" {
		s.recordAudit(r, u, "config.change", "assistant", object, audit.StatusDenied, "", nil, nil, "forbidden")
		writeError(w, http.StatusForbidden, "forbidden")
		return
	}
	var req assistantPatchRequest
	if !decodeStrictJSON(w, r, &req) {
		return
	}
	if !validAssistantPatch(w, req) {
		return
	}
	started := time.Now()
	updated, err := s.catalog.UpdateAssistant(r.Context(), id, u.ClassID, catalog.AssistantPatch{
		Name: req.Name, SystemPrompt: req.SystemPrompt, Enabled: req.Enabled,
	})
	duration := int(time.Since(started).Milliseconds())
	if err != nil {
		if errors.Is(err, catalog.ErrNotFound) {
			s.recordAudit(r, u, "config.change", "assistant", object, audit.StatusDenied, "", &duration, nil, "not_found")
			writeError(w, http.StatusNotFound, "not_found")
			return
		}
		s.recordAudit(r, u, "config.change", "assistant", object, audit.StatusFailure, "", &duration, nil, "unavailable")
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	s.recordAudit(r, u, "config.change", "assistant", object, audit.StatusSuccess, "", &duration, nil, "")
	writeJSON(w, http.StatusOK, updated)
}

func decodeStrictJSON(w http.ResponseWriter, r *http.Request, dest any) bool {
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.DisallowUnknownFields()
	if err := dec.Decode(dest); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return false
	}
	return true
}

func validSkillPatch(w http.ResponseWriter, req skillPatchRequest) bool {
	if req.Name != nil {
		n := strings.TrimSpace(*req.Name)
		if len(n) < 1 || len(n) > 255 {
			writeError(w, http.StatusBadRequest, "invalid_request")
			return false
		}
	}
	if req.Description != nil && len(*req.Description) > 2000 {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return false
	}
	return true
}

func validAssistantPatch(w http.ResponseWriter, req assistantPatchRequest) bool {
	if req.Name != nil {
		n := strings.TrimSpace(*req.Name)
		if len(n) < 1 || len(n) > 255 {
			writeError(w, http.StatusBadRequest, "invalid_request")
			return false
		}
	}
	if req.SystemPrompt != nil && len(*req.SystemPrompt) > 8000 {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return false
	}
	return true
}
