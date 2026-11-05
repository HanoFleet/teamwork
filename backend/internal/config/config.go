package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

// Config 全部来自环境变量。缺任何一项都返回错误，不填默认密钥。
type Config struct {
	SessionSecret        string
	AppVersion           string
	DBHost               string
	DBPort               string
	DBUser               string
	DBPassword           string
	DBName               string
	UploadDir            string
	MaxUploadBytes       int64
	SessionTTL           time.Duration
	ShutdownTimeout      time.Duration
	SeedTeacherPassword  string
	SeedStudentAPassword string
	SeedStudentBPassword string
	LoginFailThreshold   int
	LoginLock            time.Duration
	APIAddr              string
	QdrantURL            string
	EmbeddingURL         string
	EmbeddingAPIKey      string
	EmbeddingModel       string
	ChatURL              string
	ChatAPIKey           string
	ChatModel            string
	RabbitMQURL          string
	QueueGrade           string
	QueueDead            string
	GradeMaxAttempts     int
	GradeRetryBase       time.Duration
	GradeRetryMax        time.Duration
	GradeJitter          time.Duration
	GradeVisibility      time.Duration
	GradeModelTimeout    time.Duration
	GradeLocalDelay      time.Duration
	TaskPollFirst        time.Duration
	TaskPollLater        time.Duration
	TaskPollMax          time.Duration
}

func Load() (Config, error) {
	var missing []string
	need := func(key string) string {
		v := strings.TrimSpace(os.Getenv(key))
		if v == "" {
			missing = append(missing, key)
		}
		return v
	}

	cfg := Config{
		SessionSecret:        need("SESSION_SECRET"),
		AppVersion:           need("APP_VERSION"),
		DBHost:               need("DB_HOST"),
		DBPort:               need("DB_PORT"),
		DBUser:               need("DB_USER"),
		DBPassword:           need("DB_PASSWORD"),
		DBName:               need("DB_NAME"),
		UploadDir:            need("UPLOAD_DIR"),
		SeedTeacherPassword:  need("SEED_TEACHER_PASSWORD"),
		SeedStudentAPassword: need("SEED_STUDENT_A_PASSWORD"),
		SeedStudentBPassword: need("SEED_STUDENT_B_PASSWORD"),
		APIAddr:              need("API_ADDR"),
		QdrantURL:            need("QDRANT_URL"),
		EmbeddingURL:         need("EMBEDDING_URL"),
		EmbeddingAPIKey:      need("EMBEDDING_API_KEY"),
		EmbeddingModel:       need("EMBEDDING_MODEL"),
		ChatURL:              need("CHAT_URL"),
		ChatAPIKey:           need("CHAT_API_KEY"),
		ChatModel:            need("CHAT_MODEL"),
		RabbitMQURL:          need("RABBITMQ_URL"),
		QueueGrade:           need("QUEUE_GRADE"),
		QueueDead:            need("QUEUE_DEAD"),
	}
	maxRaw := need("MAX_UPLOAD_BYTES")
	ttlRaw := need("SESSION_TTL_HOURS")
	failRaw := need("LOGIN_FAIL_THRESHOLD")
	lockRaw := need("LOGIN_LOCK_MINUTES")
	shutdownRaw := need("SHUTDOWN_TIMEOUT_SECONDS")
	maxAttemptsRaw := need("GRADE_MAX_ATTEMPTS")
	retryBaseRaw := need("GRADE_RETRY_BASE_SECONDS")
	retryMaxRaw := need("GRADE_RETRY_MAX_SECONDS")
	jitterRaw := need("GRADE_JITTER_MS")
	visRaw := need("GRADE_VISIBILITY_TIMEOUT_SECONDS")
	modelTORaw := need("GRADE_MODEL_TIMEOUT_SECONDS")
	delayRaw := need("GRADE_LOCAL_DELAY_MS")
	pollFirstRaw := need("TASK_POLL_FIRST_MS")
	pollLaterRaw := need("TASK_POLL_LATER_MS")
	pollMaxRaw := need("TASK_POLL_MAX_SECONDS")
	if len(missing) > 0 {
		return Config{}, fmt.Errorf("missing required env: %s", strings.Join(missing, ", "))
	}
	if len(cfg.SessionSecret) < 16 {
		return Config{}, fmt.Errorf("SESSION_SECRET must be at least 16 characters")
	}
	for _, pair := range []struct {
		name string
		val  string
	}{
		{"SEED_TEACHER_PASSWORD", cfg.SeedTeacherPassword},
		{"SEED_STUDENT_A_PASSWORD", cfg.SeedStudentAPassword},
		{"SEED_STUDENT_B_PASSWORD", cfg.SeedStudentBPassword},
	} {
		if len(pair.val) < 8 {
			return Config{}, fmt.Errorf("%s must be at least 8 characters", pair.name)
		}
	}

	maxBytes, err := strconv.ParseInt(maxRaw, 10, 64)
	if err != nil || maxBytes <= 0 || maxBytes > 16<<20 {
		return Config{}, fmt.Errorf("MAX_UPLOAD_BYTES must be an integer from 1 to 16777216")
	}
	ttlHours, err := strconv.Atoi(ttlRaw)
	if err != nil || ttlHours <= 0 {
		return Config{}, fmt.Errorf("SESSION_TTL_HOURS must be a positive integer")
	}
	failN, err := strconv.Atoi(failRaw)
	if err != nil || failN <= 0 {
		return Config{}, fmt.Errorf("LOGIN_FAIL_THRESHOLD must be a positive integer")
	}
	lockMin, err := strconv.Atoi(lockRaw)
	if err != nil || lockMin <= 0 {
		return Config{}, fmt.Errorf("LOGIN_LOCK_MINUTES must be a positive integer")
	}
	shutdownSec, err := strconv.Atoi(shutdownRaw)
	if err != nil || shutdownSec < 1 || shutdownSec > 30 {
		return Config{}, fmt.Errorf("SHUTDOWN_TIMEOUT_SECONDS must be an integer from 1 to 30")
	}
	if _, err := strconv.Atoi(cfg.DBPort); err != nil {
		return Config{}, fmt.Errorf("DB_PORT must be numeric")
	}
	maxAttempts, err := strconv.Atoi(maxAttemptsRaw)
	if err != nil || maxAttempts < 1 || maxAttempts > 20 {
		return Config{}, fmt.Errorf("GRADE_MAX_ATTEMPTS must be an integer from 1 to 20")
	}
	retryBase, err := strconv.Atoi(retryBaseRaw)
	if err != nil || retryBase < 1 {
		return Config{}, fmt.Errorf("GRADE_RETRY_BASE_SECONDS must be a positive integer")
	}
	retryMax, err := strconv.Atoi(retryMaxRaw)
	if err != nil || retryMax < retryBase {
		return Config{}, fmt.Errorf("GRADE_RETRY_MAX_SECONDS must be >= GRADE_RETRY_BASE_SECONDS")
	}
	jitterMS, err := strconv.Atoi(jitterRaw)
	if err != nil || jitterMS < 0 || jitterMS > 5000 {
		return Config{}, fmt.Errorf("GRADE_JITTER_MS must be an integer from 0 to 5000")
	}
	visSec, err := strconv.Atoi(visRaw)
	if err != nil || visSec < 10 || visSec > 600 {
		return Config{}, fmt.Errorf("GRADE_VISIBILITY_TIMEOUT_SECONDS must be an integer from 10 to 600")
	}
	modelTO, err := strconv.Atoi(modelTORaw)
	if err != nil || modelTO < 1 || modelTO > 120 {
		return Config{}, fmt.Errorf("GRADE_MODEL_TIMEOUT_SECONDS must be an integer from 1 to 120")
	}
	delayMS, err := strconv.Atoi(delayRaw)
	if err != nil || delayMS < 0 || delayMS > 60000 {
		return Config{}, fmt.Errorf("GRADE_LOCAL_DELAY_MS must be an integer from 0 to 60000")
	}
	pollFirst, err := strconv.Atoi(pollFirstRaw)
	if err != nil || pollFirst < 100 || pollFirst > 10000 {
		return Config{}, fmt.Errorf("TASK_POLL_FIRST_MS must be an integer from 100 to 10000")
	}
	pollLater, err := strconv.Atoi(pollLaterRaw)
	if err != nil || pollLater < 100 || pollLater > 10000 {
		return Config{}, fmt.Errorf("TASK_POLL_LATER_MS must be an integer from 100 to 10000")
	}
	pollMax, err := strconv.Atoi(pollMaxRaw)
	if err != nil || pollMax < 5 || pollMax > 300 {
		return Config{}, fmt.Errorf("TASK_POLL_MAX_SECONDS must be an integer from 5 to 300")
	}
	if !strings.HasPrefix(cfg.RabbitMQURL, "amqp://") && !strings.HasPrefix(cfg.RabbitMQURL, "amqps://") {
		return Config{}, fmt.Errorf("RABBITMQ_URL must start with amqp:// or amqps://")
	}

	cfg.MaxUploadBytes = maxBytes
	cfg.SessionTTL = time.Duration(ttlHours) * time.Hour
	cfg.LoginFailThreshold = failN
	cfg.LoginLock = time.Duration(lockMin) * time.Minute
	cfg.ShutdownTimeout = time.Duration(shutdownSec) * time.Second
	cfg.GradeMaxAttempts = maxAttempts
	cfg.GradeRetryBase = time.Duration(retryBase) * time.Second
	cfg.GradeRetryMax = time.Duration(retryMax) * time.Second
	cfg.GradeJitter = time.Duration(jitterMS) * time.Millisecond
	cfg.GradeVisibility = time.Duration(visSec) * time.Second
	cfg.GradeModelTimeout = time.Duration(modelTO) * time.Second
	cfg.GradeLocalDelay = time.Duration(delayMS) * time.Millisecond
	cfg.TaskPollFirst = time.Duration(pollFirst) * time.Millisecond
	cfg.TaskPollLater = time.Duration(pollLater) * time.Millisecond
	cfg.TaskPollMax = time.Duration(pollMax) * time.Second
	return cfg, nil
}
