package httpapi

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strconv"
	"time"

	"campusclaw/internal/grading"
)

func (s *Server) listAssignments(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	list, err := s.grades.ListAssignments(r.Context(), actorOf(u))
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return
	}
	type item struct {
		ID        int64  `json:"id"`
		Title     string `json:"title"`
		Published bool   `json:"published"`
		CreatedAt string `json:"created_at"`
	}
	out := make([]item, 0, len(list))
	for _, row := range list {
		out = append(out, item{
			ID:        row.ID,
			Title:     row.Title,
			Published: row.Published,
			CreatedAt: row.CreatedAt.UTC().Format(time.RFC3339),
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"assignments": out})
}

func (s *Server) createSubmission(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	id, ok := parsePositiveID(r.PathValue("id"))
	if !ok {
		writeError(w, http.StatusNotFound, "not_found")
		return
	}
	var req struct {
		Body string `json:"body"`
	}
	if !decodeJSONBody(w, r, &req) {
		return
	}
	row, created, err := s.grades.Submit(r.Context(), actorOf(u), id, req.Body)
	if mapGradeErr(w, err) {
		return
	}
	status := http.StatusOK
	if created {
		status = http.StatusCreated
	}
	writeJSON(w, status, map[string]any{
		"submission_id": row.ID,
		"version":       row.Version,
		"status":        row.Status,
	})
}

func (s *Server) gradeSubmission(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	id, ok := parsePositiveID(r.PathValue("id"))
	if !ok {
		writeError(w, http.StatusNotFound, "not_found")
		return
	}
	task, result, _, err := s.grades.EnqueueGrade(r.Context(), actorOf(u), id)
	if mapGradeErr(w, err) {
		return
	}
	if result != nil {
		writeJSON(w, http.StatusOK, map[string]any{
			"task_id": task.TaskID,
			"status":  grading.StatusSucceeded,
			"result":  resultJSON(result),
		})
		return
	}
	if task.Status == grading.StatusFailed || task.Status == grading.StatusDead {
		body := map[string]any{"task_id": task.TaskID, "status": task.Status}
		if task.Error != "" {
			body["error"] = task.Error
		}
		writeJSON(w, http.StatusOK, body)
		return
	}
	writeJSON(w, http.StatusAccepted, map[string]string{
		"task_id":    task.TaskID,
		"status":     grading.StatusPending,
		"status_url": "/api/tasks/" + task.TaskID,
	})
}

func (s *Server) getTask(w http.ResponseWriter, r *http.Request) {
	u, ok := s.requireUser(w, r)
	if !ok {
		return
	}
	taskID := r.PathValue("task_id")
	task, result, err := s.grades.GetTask(r.Context(), actorOf(u), taskID)
	if mapGradeErr(w, err) {
		return
	}
	view := map[string]any{
		"task_id":    task.TaskID,
		"type":       grading.TaskTypeGrade,
		"status":     task.Status,
		"attempts":   task.Attempts,
		"created_at": task.CreatedAt.UTC().Format(time.RFC3339),
	}
	if task.StartedAt != nil {
		view["started_at"] = task.StartedAt.UTC().Format(time.RFC3339)
	}
	if task.FinishedAt != nil {
		view["finished_at"] = task.FinishedAt.UTC().Format(time.RFC3339)
	}
	if task.Error != "" {
		view["error"] = task.Error
	}
	if result != nil {
		view["result"] = resultJSON(result)
	}
	writeJSON(w, http.StatusOK, view)
}

func resultJSON(result *grading.Result) map[string]any {
	return map[string]any{
		"score":     result.Score,
		"feedback":  result.Feedback,
		"sources":   []string{"本地评分规则（关键词覆盖与篇幅）"},
		"graded_at": result.GradedAt.UTC().Format(time.RFC3339),
	}
}

func actorOf(u *User) grading.Actor {
	return grading.Actor{ID: u.ID, Role: u.Role, ClassID: u.ClassID}
}

func parsePositiveID(raw string) (int64, bool) {
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id <= 0 {
		return 0, false
	}
	return id, true
}

func decodeJSONBody(w http.ResponseWriter, r *http.Request, dest any) bool {
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	if err := dec.Decode(dest); err != nil && !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return false
	}
	return true
}

func mapGradeErr(w http.ResponseWriter, err error) bool {
	if err == nil {
		return false
	}
	switch {
	case errors.Is(err, grading.ErrInvalid):
		writeError(w, http.StatusBadRequest, "invalid_request")
	case errors.Is(err, grading.ErrForbidden):
		writeError(w, http.StatusForbidden, "forbidden")
	case errors.Is(err, grading.ErrNotFound):
		writeError(w, http.StatusNotFound, "not_found")
	default:
		writeError(w, http.StatusServiceUnavailable, "unavailable")
	}
	return true
}
