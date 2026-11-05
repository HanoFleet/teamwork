package grading

import "fmt"

func IsTerminal(status string) bool {
	return status == StatusSucceeded || status == StatusFailed || status == StatusDead
}

func CanStart(status string) error {
	switch status {
	case StatusPending:
		return nil
	case StatusRunning:
		return nil
	case StatusSucceeded, StatusFailed, StatusDead:
		return fmt.Errorf("%w: %s", ErrIllegalState, status)
	default:
		return fmt.Errorf("%w: unknown %s", ErrIllegalState, status)
	}
}

func OnStart(status string) (string, error) {
	if err := CanStart(status); err != nil {
		return "", err
	}
	return StatusRunning, nil
}

func OnSuccess(status string) (string, error) {
	if status != StatusRunning && status != StatusPending {
		return "", fmt.Errorf("%w: cannot succeed from %s", ErrIllegalState, status)
	}
	return StatusSucceeded, nil
}

func OnFailure(status string, attempts, maxAttempts int, transient bool) (string, error) {
	if status != StatusRunning && status != StatusPending {
		return "", fmt.Errorf("%w: cannot fail from %s", ErrIllegalState, status)
	}
	if !transient {
		return StatusFailed, nil
	}
	if attempts >= maxAttempts {
		return StatusDead, nil
	}
	return StatusPending, nil
}

func RetrySecondsForAttempt(attempts int) int {
	switch {
	case attempts <= 1:
		return 1
	case attempts == 2:
		return 2
	case attempts == 3:
		return 4
	case attempts == 4:
		return 8
	default:
		return 16
	}
}
