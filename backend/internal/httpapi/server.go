package httpapi

import (
	"context"
	"crypto/subtle"
	"database/sql"
	"errors"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"strings"
	"time"

	"campusclaw/internal/audit"
	"campusclaw/internal/auth"
	"campusclaw/internal/catalog"
	"campusclaw/internal/chat"
	"campusclaw/internal/config"
	"campusclaw/internal/embed"
	"campusclaw/internal/grading"
	"campusclaw/internal/health"
	"campusclaw/internal/logging"
	"campusclaw/internal/qdrant"
	"campusclaw/internal/retrieval"
)

const cookieName = "campusclaw_session"

type User struct {
	ID        int64
	Username  string
	Role      string
	ClassID   int64
	ClassName string
	CSRFToken string
}

type Server struct {
	cfg     config.Config
	db      *sql.DB
	limiter *auth.Limiter
	mux     *http.ServeMux
	retr    *retrieval.Service
	grades  *grading.Service
	catalog *catalog.Store
	audit   *audit.Store
	health  *health.Checker
	logger  *slog.Logger
}

func New(cfg config.Config, db *sql.DB, logger *slog.Logger) *Server {
	emb := embed.New(cfg.EmbeddingURL, cfg.EmbeddingAPIKey, cfg.EmbeddingModel)
	qd := qdrant.New(cfg.QdrantURL, emb.Dim())
	s := &Server{
		cfg:     cfg,
		db:      db,
		limiter: auth.NewLimiter(),
		mux:     http.NewServeMux(),
		retr:    retrieval.New(db, emb, qd, chat.New(cfg.ChatURL, cfg.ChatAPIKey, cfg.ChatModel)),
		grades:  grading.NewService(db, cfg),
		catalog: catalog.NewStore(db),
		audit:   audit.NewStore(db),
		logger:  logger,
		health: &health.Checker{
			PingDB:      func(ctx context.Context) error { return db.PingContext(ctx) },
			QdrantOK:    qd.Available,
			EmbeddingOK: cfg.EmbeddingURL != "" && cfg.EmbeddingModel != "",
			Version:     cfg.AppVersion,
			Now:         time.Now,
			Timeout:     2 * time.Second,
		},
	}
	s.mux.HandleFunc("GET /live", s.live)
	s.mux.HandleFunc("GET /health", s.ready)
	s.mux.HandleFunc("GET /ready", s.ready)
	s.mux.HandleFunc("POST /api/login", s.login)
	s.mux.HandleFunc("POST /api/logout", s.logout)
	s.mux.HandleFunc("GET /api/me", s.me)
	s.mux.HandleFunc("GET /api/materials", s.listMaterials)
	s.mux.HandleFunc("POST /api/materials", s.uploadMaterial)
	s.mux.HandleFunc("GET /api/materials/{id}", s.getMaterial)
	s.mux.HandleFunc("GET /api/materials/{id}/file", s.getMaterialFile)
	s.mux.HandleFunc("POST /api/materials/{id}/reindex", s.reindex)
	s.mux.HandleFunc("POST /api/search", s.search)
	s.mux.HandleFunc("POST /api/ask", s.ask)
	s.mux.HandleFunc("GET /api/assignments", s.listAssignments)
	s.mux.HandleFunc("POST /api/assignments/{id}/submissions", s.createSubmission)
	s.mux.HandleFunc("POST /api/submissions/{id}/grade", s.gradeSubmission)
	s.mux.HandleFunc("GET /api/tasks/{task_id}", s.getTask)
	s.mux.HandleFunc("GET /api/skills", s.listSkills)
	s.mux.HandleFunc("PATCH /api/skills/{key}", s.patchSkill)
	s.mux.HandleFunc("GET /api/assistants", s.listAssistants)
	s.mux.HandleFunc("PATCH /api/assistants/{id}", s.patchAssistant)
	s.mux.HandleFunc("POST /api/skills/{key}/run", s.runSkill)
	s.mux.HandleFunc("GET /api/audit-logs", s.listAuditLogs)
	return s
}

func (s *Server) Backfill(ctx context.Context) error {
	if s.retr == nil {
		return nil
	}
	return s.retr.Backfill(ctx)
}

func (s *Server) Handler() http.Handler { return logging.Middleware(s.mux, s.logger) }

func (s *Server) live(w http.ResponseWriter, r *http.Request) {
	if r.URL.RawQuery != "" {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}
	writeJSON(w, http.StatusOK, s.health.Live())
}

func (s *Server) ready(w http.ResponseWriter, r *http.Request) {
	if r.URL.RawQuery != "" {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}
	result, ok := s.health.Ready(r.Context())
	status := http.StatusOK
	if !ok {
		status = http.StatusServiceUnavailable
	}
	writeJSON(w, status, result)
}

func sessionIDFromRequest(secret string, r *http.Request) (string, bool, bool) {
	if raw := strings.TrimSpace(r.Header.Get("Authorization")); raw != "" {
		scheme, token, ok := strings.Cut(raw, " ")
		if ok && strings.EqualFold(scheme, "Bearer") && token != "" {
			if sessionID, parsed := auth.ParseJWT(secret, token); parsed {
				return sessionID, true, true
			}
		}
	}
	c, err := r.Cookie(cookieName)
	if err != nil || c.Value == "" {
		return "", false, false
	}
	sessionID, ok := auth.Open(secret, c.Value)
	return sessionID, false, ok
}

func (s *Server) currentUser(r *http.Request) (*User, bool, error) {
	sessionID, viaBearer, ok := sessionIDFromRequest(s.cfg.SessionSecret, r)
	if !ok {
		return nil, false, errNoSession
	}
	var u User
	var expires time.Time
	err := s.db.QueryRowContext(r.Context(), `SELECT u.id, u.username, u.role, u.class_id, c.name, COALESCE(s.csrf_token,''), s.expires_at
		FROM sessions s
		JOIN users u ON u.id = s.user_id
		JOIN classes c ON c.id = u.class_id
		WHERE s.id = ?`, sessionID).Scan(&u.ID, &u.Username, &u.Role, &u.ClassID, &u.ClassName, &u.CSRFToken, &expires)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, viaBearer, errNoSession
	}
	if err != nil {
		return nil, viaBearer, err
	}
	if !expires.After(time.Now().UTC()) {
		_, _ = s.db.ExecContext(r.Context(), `DELETE FROM sessions WHERE id=?`, sessionID)
		return nil, viaBearer, errNoSession
	}
	return &u, viaBearer, nil
}

func (s *Server) requireUser(w http.ResponseWriter, r *http.Request) (*User, bool) {
	if !s.databaseUp(r.Context()) {
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return nil, false
	}
	u, viaBearer, err := s.currentUser(r)
	if err != nil {
		if errors.Is(err, errNoSession) {
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return nil, false
		}
		writeError(w, http.StatusServiceUnavailable, "unavailable")
		return nil, false
	}
	if !viaBearer && isUnsafeMethod(r.Method) {
		if !sameOrigin(r) {
			s.recordAudit(r, u, "csrf.check", "request", r.URL.Path, audit.StatusDenied, "", nil, nil, "origin_rejected")
			writeError(w, http.StatusForbidden, "csrf_invalid")
			return nil, false
		}
		token := r.Header.Get("X-CSRF-Token")
		if u.CSRFToken == "" || subtle.ConstantTimeCompare([]byte(token), []byte(u.CSRFToken)) != 1 {
			s.recordAudit(r, u, "csrf.check", "request", r.URL.Path, audit.StatusDenied, "", nil, nil, "csrf_invalid")
			writeError(w, http.StatusForbidden, "csrf_invalid")
			return nil, false
		}
	}
	return u, true
}

func isUnsafeMethod(method string) bool {
	switch method {
	case http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete:
		return true
	default:
		return false
	}
}

func sameOrigin(r *http.Request) bool {
	raw := strings.TrimSpace(r.Header.Get("Origin"))
	if raw == "" {
		raw = strings.TrimSpace(r.Header.Get("Referer"))
	}
	if raw == "" {
		return true
	}
	u, err := url.Parse(raw)
	if err != nil {
		return false
	}
	return strings.EqualFold(u.Host, r.Host)
}

func (s *Server) setSessionCookie(w http.ResponseWriter, sealed string) {
	http.SetCookie(w, &http.Cookie{
		Name:     cookieName,
		Value:    sealed,
		Path:     "/",
		MaxAge:   int(s.cfg.SessionTTL.Seconds()),
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})
}

func (s *Server) clearSessionCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     cookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})
}

func (s *Server) databaseUp(ctx context.Context) bool {
	pingCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	return s.db.PingContext(pingCtx) == nil
}

func clientIP(r *http.Request) string {
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		first := strings.TrimSpace(strings.Split(xff, ",")[0])
		if first != "" {
			return first
		}
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

var errNoSession = errors.New("no session")
