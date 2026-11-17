package httpapi

import (
	"net/http"
	"strconv"
	"strings"
	"time"

	"campusclaw/internal/audit"
	"campusclaw/internal/logging"
)

func (s *Server) recordAudit(r *http.Request, u *User, operation, objectType, objectID, status, skillKey string, duration *int, usage map[string]any, errorCode string) {
	if s.audit == nil {
		return
	}
	entry := audit.Entry{
		OccurredAt:   time.Now().UTC(),
		Operation:    operation,
		ObjectType:   objectType,
		ObjectID:     objectID,
		ResultStatus: status,
		SkillKey:     skillKey,
		DurationMS:   duration,
		Usage:        usage,
		ErrorCode:    errorCode,
		RequestID:    logging.RequestID(r.Context()),
	}
	if u != nil {
		entry.OperatorID = u.ID
		entry.OperatorUsername = u.Username
		entry.OperatorRole = u.Role
		entry.ClassID = u.ClassID
	} else {
		entry.OperatorUsername = "anonymous"
		entry.OperatorRole = "system"
	}
	if err := s.audit.Append(r.Context(), entry); err != nil && s.logger != nil {
		s.logger.Error("audit_insert", "event", "audit", "reason", err.Error())
	}
}

func (s *Server) listAuditLogs(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	if u.Role != "teacher" {
		s.recordAudit(r, u, "audit.query", "audit", "list", audit.StatusDenied, "", nil, nil, "forbidden")
		writeError(w, http.StatusForbidden, "forbidden")
		return
	}
	if s.audit == nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	filter := audit.Filter{ClassID: u.ClassID, Limit: 100}
	query := r.URL.Query()
	if raw := strings.TrimSpace(query.Get("limit")); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 100 {
			writeError(w, http.StatusBadRequest, "invalid_request")
			return
		}
		filter.Limit = n
	}
	if raw := strings.TrimSpace(query.Get("skill_key")); raw != "" {
		if len(raw) > 64 {
			writeError(w, http.StatusBadRequest, "invalid_request")
			return
		}
		filter.SkillKey = raw
	}
	if raw := strings.TrimSpace(query.Get("operator_id")); raw != "" {
		n, err := strconv.ParseInt(raw, 10, 64)
		if err != nil || n <= 0 {
			writeError(w, http.StatusBadRequest, "invalid_request")
			return
		}
		filter.OperatorID = n
	}
	for key, dest := range map[string]*time.Time{"from": &filter.From, "to": &filter.To} {
		if raw := strings.TrimSpace(query.Get(key)); raw != "" {
			t, err := time.Parse(time.RFC3339, raw)
			if err != nil {
				writeError(w, http.StatusBadRequest, "invalid_request")
				return
			}
			*dest = t.UTC()
		}
	}
	if !filter.From.IsZero() && !filter.To.IsZero() && filter.To.Before(filter.From) {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}
	logs, err := s.audit.List(r.Context(), filter)
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"logs": logs})
}
