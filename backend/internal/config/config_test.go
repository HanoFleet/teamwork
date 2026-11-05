package config

import (
	"testing"
	"time"
)

func TestLoadRejectsMissingSecret(t *testing.T) {
	for _, k := range []string{
		"SESSION_SECRET", "APP_VERSION", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME",
		"UPLOAD_DIR", "MAX_UPLOAD_BYTES", "SESSION_TTL_HOURS",
		"SEED_TEACHER_PASSWORD", "SEED_STUDENT_A_PASSWORD", "SEED_STUDENT_B_PASSWORD",
		"LOGIN_FAIL_THRESHOLD", "LOGIN_LOCK_MINUTES", "SHUTDOWN_TIMEOUT_SECONDS", "API_ADDR",
		"QDRANT_URL", "EMBEDDING_URL", "EMBEDDING_API_KEY", "EMBEDDING_MODEL",
		"CHAT_URL", "CHAT_API_KEY", "CHAT_MODEL",
		"RABBITMQ_URL", "QUEUE_GRADE", "QUEUE_DEAD",
		"GRADE_MAX_ATTEMPTS", "GRADE_RETRY_BASE_SECONDS", "GRADE_RETRY_MAX_SECONDS",
		"GRADE_JITTER_MS", "GRADE_VISIBILITY_TIMEOUT_SECONDS", "GRADE_MODEL_TIMEOUT_SECONDS",
		"GRADE_LOCAL_DELAY_MS", "TASK_POLL_FIRST_MS", "TASK_POLL_LATER_MS", "TASK_POLL_MAX_SECONDS",
	} {
		t.Setenv(k, "")
	}
	if _, err := Load(); err == nil {
		t.Fatal("expected error when env is empty")
	}
}

func TestLoadAcceptsExplicitEnv(t *testing.T) {
	t.Setenv("SESSION_SECRET", "0123456789abcdef")
	t.Setenv("APP_VERSION", "test-version")
	t.Setenv("DB_HOST", "db")
	t.Setenv("DB_PORT", "3306")
	t.Setenv("DB_USER", "campusclaw")
	t.Setenv("DB_PASSWORD", "app-secret")
	t.Setenv("DB_NAME", "campusclaw")
	t.Setenv("UPLOAD_DIR", "/data/uploads")
	t.Setenv("MAX_UPLOAD_BYTES", "1048576")
	t.Setenv("SESSION_TTL_HOURS", "12")
	t.Setenv("SEED_TEACHER_PASSWORD", "teacher-pass")
	t.Setenv("SEED_STUDENT_A_PASSWORD", "student-a-pass")
	t.Setenv("SEED_STUDENT_B_PASSWORD", "student-b-pass")
	t.Setenv("LOGIN_FAIL_THRESHOLD", "5")
	t.Setenv("LOGIN_LOCK_MINUTES", "15")
	t.Setenv("SHUTDOWN_TIMEOUT_SECONDS", "10")
	t.Setenv("API_ADDR", ":8080")
	t.Setenv("QDRANT_URL", "http://qdrant:6333")
	t.Setenv("EMBEDDING_URL", "local")
	t.Setenv("EMBEDDING_API_KEY", "local")
	t.Setenv("EMBEDDING_MODEL", "local-ngram-256")
	t.Setenv("CHAT_URL", "local")
	t.Setenv("CHAT_API_KEY", "local")
	t.Setenv("CHAT_MODEL", "local-extractive")
	t.Setenv("RABBITMQ_URL", "amqp://campusclaw:secret@rabbitmq:5672/")
	t.Setenv("QUEUE_GRADE", "grade.tasks")
	t.Setenv("QUEUE_DEAD", "grade.dead")
	t.Setenv("GRADE_MAX_ATTEMPTS", "5")
	t.Setenv("GRADE_RETRY_BASE_SECONDS", "1")
	t.Setenv("GRADE_RETRY_MAX_SECONDS", "16")
	t.Setenv("GRADE_JITTER_MS", "250")
	t.Setenv("GRADE_VISIBILITY_TIMEOUT_SECONDS", "60")
	t.Setenv("GRADE_MODEL_TIMEOUT_SECONDS", "30")
	t.Setenv("GRADE_LOCAL_DELAY_MS", "0")
	t.Setenv("TASK_POLL_FIRST_MS", "1000")
	t.Setenv("TASK_POLL_LATER_MS", "2000")
	t.Setenv("TASK_POLL_MAX_SECONDS", "60")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.MaxUploadBytes != 1048576 || cfg.LoginFailThreshold != 5 || cfg.AppVersion != "test-version" || cfg.ShutdownTimeout != 10*time.Second {
		t.Fatalf("parsed config = %+v", cfg)
	}
	if cfg.GradeMaxAttempts != 5 || cfg.QueueGrade != "grade.tasks" || cfg.TaskPollMax != 60*time.Second {
		t.Fatalf("parsed grade config = %+v", cfg)
	}
}
