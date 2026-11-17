#!/usr/bin/env python3
"""Generate a throwaway .env for the CI verify/e2e job."""

from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
password = secrets.token_hex(16)
values = {
    "WEB_PORT": "8080",
    "APP_VERSION": "v2.0.0-ci",
    "SHUTDOWN_TIMEOUT_SECONDS": "10",
    "MYSQL_ROOT_PASSWORD": secrets.token_hex(24),
    "DB_NAME": "campusclaw",
    "DB_USER": "campusclaw",
    "DB_PASSWORD": secrets.token_hex(24),
    "SESSION_SECRET": secrets.token_hex(32),
    "SEED_TEACHER_PASSWORD": secrets.token_hex(12),
    "SEED_STUDENT_A_PASSWORD": secrets.token_hex(12),
    "SEED_STUDENT_B_PASSWORD": secrets.token_hex(12),
    "MAX_UPLOAD_BYTES": "1048576",
    "SESSION_TTL_HOURS": "12",
    "LOGIN_FAIL_THRESHOLD": "5",
    "LOGIN_LOCK_MINUTES": "15",
    "QDRANT_URL": "http://qdrant:6333",
    "EMBEDDING_URL": "local",
    "EMBEDDING_API_KEY": "local",
    "EMBEDDING_MODEL": "local-ngram-256",
    "CHAT_URL": "local",
    "CHAT_API_KEY": "local",
    "CHAT_MODEL": "local-extractive",
    "RABBITMQ_DEFAULT_USER": "campusclaw",
    "RABBITMQ_DEFAULT_PASS": password,
    "RABBITMQ_URL": f"amqp://campusclaw:{password}@rabbitmq:5672/",
    "QUEUE_GRADE": "grade.tasks",
    "QUEUE_DEAD": "grade.dead",
    "GRADE_MAX_ATTEMPTS": "5",
    "GRADE_RETRY_BASE_SECONDS": "1",
    "GRADE_RETRY_MAX_SECONDS": "16",
    "GRADE_JITTER_MS": "250",
    "GRADE_VISIBILITY_TIMEOUT_SECONDS": "60",
    "GRADE_MODEL_TIMEOUT_SECONDS": "30",
    "GRADE_LOCAL_DELAY_MS": "2000",
    "TASK_POLL_FIRST_MS": "1000",
    "TASK_POLL_LATER_MS": "2000",
    "TASK_POLL_MAX_SECONDS": "60",
}
(ROOT / ".env").write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
