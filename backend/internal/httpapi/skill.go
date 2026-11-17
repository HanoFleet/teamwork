package httpapi

import (
	"errors"
	"net/http"
	"strconv"
	"strings"
	"time"

	"campusclaw/internal/audit"
	"campusclaw/internal/grading"
)

type skillRunRequest struct {
	SubmissionID int64 `json:"submission_id"`
}

func (s *Server) runSkill(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	key := strings.TrimSpace(r.PathValue("key"))
	object := "skill:" + key
	if s.catalog == nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	skill, err := s.catalog.GetSkill(r.Context(), key)
	if err != nil || !skill.Enabled || key != "grade" {
		s.recordAudit(r, u, "skill.run", "skill", object, audit.StatusDenied, key, nil, nil, "not_found")
		writeError(w, http.StatusNotFound, "not_found")
		return
	}
	var req skillRunRequest
	if !decodeJSONBody(w, r, &req) {
		return
	}
	if req.SubmissionID <= 0 {
		s.recordAudit(r, u, "skill.run", "submission", "0", audit.StatusDenied, key, nil, nil, "invalid_request")
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}
	object = "submission:" + strconv.FormatInt(req.SubmissionID, 10)
	started := time.Now()
	task, result, _, err := s.grades.EnqueueGrade(r.Context(), actorOf(u), req.SubmissionID)
	duration := int(time.Since(started).Milliseconds())
	usage := map[string]any{"model": "local", "tokens": 0}
	if err != nil {
		code, status := "unavailable", audit.StatusFailure
		if errors.Is(err, grading.ErrNotFound) {
			code, status = "not_found", audit.StatusDenied
		} else if errors.Is(err, grading.ErrForbidden) {
			code, status = "forbidden", audit.StatusDenied
		}
		s.recordAudit(r, u, "skill.run", "submission", object, status, key, &duration, usage, code)
		mapGradeErr(w, err)
		return
	}
	resultStatus := audit.StatusAccepted
	if result != nil {
		resultStatus = audit.StatusSuccess
	}
	if task.Status == grading.StatusFailed || task.Status == grading.StatusDead {
		resultStatus = audit.StatusFailure
	}
	s.recordAudit(r, u, "skill.run", "submission", object, resultStatus, key, &duration, usage, "")
	writeGradeTaskResponse(w, task, result)
}
