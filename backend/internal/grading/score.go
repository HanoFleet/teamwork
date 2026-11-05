package grading

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
	"unicode/utf8"

	"campusclaw/internal/config"
)

const (
	sentinelTransient = "GRADE_TRANSIENT_FAIL"
	sentinelPermanent = "GRADE_PERMANENT_FAIL"
)

type ScoreResult struct {
	Score    float64
	Feedback string
	Sources  []string
}

func ScoreLocal(body string) ScoreResult {
	text := strings.TrimSpace(body)
	n := utf8.RuneCountInString(text)
	lengthScore := n / 40
	if lengthScore > 50 {
		lengthScore = 50
	}
	keywords := []string{"函数", "单调", "定理", "证明", "实验", "结论", "分析", "方程"}
	hits := 0
	for _, word := range keywords {
		if strings.Contains(text, word) {
			hits++
		}
	}
	keywordScore := 0
	if len(keywords) > 0 {
		keywordScore = hits * 50 / len(keywords)
	}
	score := float64(lengthScore + keywordScore)
	if score > 100 {
		score = 100
	}
	feedback := fmt.Sprintf("本次按关键词覆盖与篇幅评分，得分 %.0f。请结合课堂材料核对要点。", score)
	return ScoreResult{
		Score:    score,
		Feedback: feedback,
		Sources:  []string{"本地评分规则（关键词覆盖与篇幅）"},
	}
}

func ClassifyBody(body string) error {
	text := strings.TrimSpace(body)
	if text == "" {
		return fmt.Errorf("%w: empty body", ErrPermanent)
	}
	if strings.Contains(text, sentinelPermanent) {
		return fmt.Errorf("%w: fixture permanent", ErrPermanent)
	}
	if strings.Contains(text, sentinelTransient) {
		return fmt.Errorf("%w: fixture 429", ErrTransient)
	}
	return nil
}

func Score(ctx context.Context, cfg config.Config, body string) (ScoreResult, error) {
	if err := ClassifyBody(body); err != nil {
		return ScoreResult{}, err
	}
	if cfg.GradeLocalDelay > 0 {
		select {
		case <-ctx.Done():
			return ScoreResult{}, fmt.Errorf("%w: %v", ErrTransient, ctx.Err())
		case <-time.After(cfg.GradeLocalDelay):
		}
	}
	if strings.EqualFold(strings.TrimSpace(cfg.ChatURL), "local") {
		return ScoreLocal(body), nil
	}
	if strings.EqualFold(strings.TrimSpace(cfg.ChatAPIKey), "invalid") {
		return ScoreResult{}, fmt.Errorf("%w: invalid api key", ErrPermanent)
	}
	return scoreRemote(ctx, cfg, body)
}

type remoteGrade struct {
	Score    float64 `json:"score"`
	Feedback string  `json:"feedback"`
}

func scoreRemote(ctx context.Context, cfg config.Config, body string) (ScoreResult, error) {
	payload, err := json.Marshal(map[string]any{
		"model": cfg.ChatModel,
		"body":  body,
	})
	if err != nil {
		return ScoreResult{}, fmt.Errorf("%w: %v", ErrPermanent, err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(cfg.ChatURL, "/")+"/grade", bytes.NewReader(payload))
	if err != nil {
		return ScoreResult{}, fmt.Errorf("%w: %v", ErrPermanent, err)
	}
	req.Header.Set("Content-Type", "application/json")
	if cfg.ChatAPIKey != "" {
		req.Header.Set("Authorization", "Bearer "+cfg.ChatAPIKey)
	}
	client := &http.Client{Timeout: cfg.GradeModelTimeout}
	resp, err := client.Do(req)
	if err != nil {
		return ScoreResult{}, fmt.Errorf("%w: %v", ErrTransient, err)
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500 {
		return ScoreResult{}, fmt.Errorf("%w: http %d", ErrTransient, resp.StatusCode)
	}
	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return ScoreResult{}, fmt.Errorf("%w: http %d", ErrPermanent, resp.StatusCode)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return ScoreResult{}, fmt.Errorf("%w: http %d", ErrTransient, resp.StatusCode)
	}
	var parsed remoteGrade
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return ScoreResult{}, fmt.Errorf("%w: invalid json", ErrTransient)
	}
	if parsed.Score < 0 || parsed.Score > 100 || strings.TrimSpace(parsed.Feedback) == "" {
		return ScoreResult{}, fmt.Errorf("%w: invalid score payload", ErrTransient)
	}
	return ScoreResult{
		Score:    parsed.Score,
		Feedback: parsed.Feedback,
		Sources:  []string{cfg.ChatModel},
	}, nil
}
