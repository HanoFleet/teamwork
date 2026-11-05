package grading

import "testing"

func TestStateMachineHappyPath(t *testing.T) {
	next, err := OnStart(StatusPending)
	if err != nil || next != StatusRunning {
		t.Fatalf("start: %s %v", next, err)
	}
	next, err = OnSuccess(StatusRunning)
	if err != nil || next != StatusSucceeded {
		t.Fatalf("success: %s %v", next, err)
	}
	if !IsTerminal(StatusSucceeded) {
		t.Fatal("succeeded should be terminal")
	}
}

func TestStateMachineTransientThenDead(t *testing.T) {
	for attempts := 1; attempts <= 4; attempts++ {
		next, err := OnFailure(StatusRunning, attempts, 5, true)
		if err != nil || next != StatusPending {
			t.Fatalf("attempt %d: %s %v", attempts, next, err)
		}
	}
	next, err := OnFailure(StatusRunning, 5, 5, true)
	if err != nil || next != StatusDead {
		t.Fatalf("dead: %s %v", next, err)
	}
}

func TestStateMachinePermanentFailed(t *testing.T) {
	next, err := OnFailure(StatusRunning, 1, 5, false)
	if err != nil || next != StatusFailed {
		t.Fatalf("permanent: %s %v", next, err)
	}
}

func TestIllegalTransfers(t *testing.T) {
	if _, err := OnStart(StatusSucceeded); err == nil {
		t.Fatal("expected illegal start from succeeded")
	}
	if _, err := OnSuccess(StatusFailed); err == nil {
		t.Fatal("expected illegal success from failed")
	}
	if _, err := OnFailure(StatusDead, 1, 5, true); err == nil {
		t.Fatal("expected illegal fail from dead")
	}
}

func TestRetrySeconds(t *testing.T) {
	want := map[int]int{1: 1, 2: 2, 3: 4, 4: 8, 5: 16}
	for attempts, sec := range want {
		if got := RetrySecondsForAttempt(attempts); got != sec {
			t.Fatalf("attempt %d: got %d want %d", attempts, got, sec)
		}
	}
}
