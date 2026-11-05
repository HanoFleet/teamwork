package grading

import (
	"errors"
	"strings"
	"testing"
)

func TestScoreLocalRange(t *testing.T) {
	got := ScoreLocal("函数单调性定理证明分析实验结论方程。" + strings.Repeat("字", 400))
	if got.Score < 0 || got.Score > 100 || got.Feedback == "" {
		t.Fatalf("score=%v feedback=%q", got.Score, got.Feedback)
	}
}

func TestClassifySentinels(t *testing.T) {
	if err := ClassifyBody("   "); !errors.Is(err, ErrPermanent) {
		t.Fatalf("empty should be permanent: %v", err)
	}
	if err := ClassifyBody("ok GRADE_PERMANENT_FAIL"); !errors.Is(err, ErrPermanent) {
		t.Fatalf("permanent sentinel: %v", err)
	}
	if err := ClassifyBody("ok GRADE_TRANSIENT_FAIL"); !errors.Is(err, ErrTransient) {
		t.Fatalf("transient sentinel: %v", err)
	}
}
