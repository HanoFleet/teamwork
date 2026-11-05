package queue

import (
	"fmt"

	amqp "github.com/rabbitmq/amqp091-go"
)

const (
	ExchangeGrade = "grade"
	ExchangeDLX   = "grade.dlx"
	QueueTasks    = "grade.tasks"
	QueueDead     = "grade.dead"
	KeyTasks      = "tasks"
	KeyDead       = "dead"
)

var RetrySeconds = []int{1, 2, 4, 8, 16}

func RetryQueueName(seconds int) string {
	return fmt.Sprintf("grade.retry.%ds", seconds)
}

func RetryRoutingKey(seconds int) string {
	return fmt.Sprintf("retry.%d", seconds)
}

func Declare(ch *amqp.Channel) error {
	if err := ch.ExchangeDeclare(ExchangeGrade, "direct", true, false, false, false, nil); err != nil {
		return fmt.Errorf("declare exchange %s: %w", ExchangeGrade, err)
	}
	if err := ch.ExchangeDeclare(ExchangeDLX, "direct", true, false, false, false, nil); err != nil {
		return fmt.Errorf("declare exchange %s: %w", ExchangeDLX, err)
	}
	if _, err := ch.QueueDeclare(QueueTasks, true, false, false, false, amqp.Table{
		"x-dead-letter-exchange":    ExchangeDLX,
		"x-dead-letter-routing-key": KeyDead,
	}); err != nil {
		return fmt.Errorf("declare queue %s: %w", QueueTasks, err)
	}
	if err := ch.QueueBind(QueueTasks, KeyTasks, ExchangeGrade, false, nil); err != nil {
		return err
	}
	for _, sec := range RetrySeconds {
		name := RetryQueueName(sec)
		if _, err := ch.QueueDeclare(name, true, false, false, false, amqp.Table{
			"x-message-ttl":             int32(sec * 1000),
			"x-dead-letter-exchange":    ExchangeGrade,
			"x-dead-letter-routing-key": KeyTasks,
		}); err != nil {
			return fmt.Errorf("declare queue %s: %w", name, err)
		}
		if err := ch.QueueBind(name, RetryRoutingKey(sec), ExchangeGrade, false, nil); err != nil {
			return err
		}
	}
	if _, err := ch.QueueDeclare(QueueDead, true, false, false, false, nil); err != nil {
		return fmt.Errorf("declare queue %s: %w", QueueDead, err)
	}
	if err := ch.QueueBind(QueueDead, KeyDead, ExchangeGrade, false, nil); err != nil {
		return err
	}
	if err := ch.QueueBind(QueueDead, KeyDead, ExchangeDLX, false, nil); err != nil {
		return err
	}
	return nil
}
