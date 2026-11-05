package queue

import "testing"

func TestRetryQueueNames(t *testing.T) {
	if RetryQueueName(1) != "grade.retry.1s" || RetryRoutingKey(16) != "retry.16" {
		t.Fatalf("retry names: %s %s", RetryQueueName(1), RetryRoutingKey(16))
	}
	if len(RetrySeconds) != 5 || RetrySeconds[4] != 16 {
		t.Fatalf("retry seconds = %v", RetrySeconds)
	}
}
