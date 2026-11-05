package grading

import "testing"

func TestIdempotencyKey(t *testing.T) {
	if got := IdempotencyKey(12, 3); got != "grade:12:3" {
		t.Fatalf("got %s", got)
	}
}
