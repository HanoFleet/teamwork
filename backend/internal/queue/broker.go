package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
)

type Payload struct {
	TaskID            string `json:"task_id"`
	SubmissionID      int64  `json:"submission_id"`
	SubmissionVersion int    `json:"submission_version"`
	Error             string `json:"error,omitempty"`
}

type Broker struct {
	url string

	mu       sync.Mutex
	conn     *amqp.Connection
	pub      *amqp.Channel
	confirms chan amqp.Confirmation
}

func New(url string) *Broker {
	return &Broker{url: url}
}

func (b *Broker) Ensure(ctx context.Context) error {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.pub != nil && !b.pub.IsClosed() && b.conn != nil && !b.conn.IsClosed() {
		return nil
	}
	return b.connectLocked()
}

func (b *Broker) connectLocked() error {
	b.closeLocked()
	conn, err := amqp.DialConfig(b.url, amqp.Config{
		Heartbeat: 10 * time.Second,
		Locale:    "en_US",
	})
	if err != nil {
		return err
	}
	ch, err := conn.Channel()
	if err != nil {
		_ = conn.Close()
		return err
	}
	if err := ch.Confirm(false); err != nil {
		_ = ch.Close()
		_ = conn.Close()
		return err
	}
	if err := Declare(ch); err != nil {
		_ = ch.Close()
		_ = conn.Close()
		return err
	}
	b.conn = conn
	b.pub = ch
	b.confirms = ch.NotifyPublish(make(chan amqp.Confirmation, 32))
	return nil
}

func (b *Broker) Publish(ctx context.Context, routingKey string, payload Payload) error {
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	if err := b.EnsureUnlocked(ctx); err != nil {
		return err
	}
	if err := b.pub.PublishWithContext(ctx, ExchangeGrade, routingKey, true, false, amqp.Publishing{
		ContentType:  "application/json",
		DeliveryMode: amqp.Persistent,
		Body:         body,
		Timestamp:    time.Now().UTC(),
	}); err != nil {
		b.closeLocked()
		return err
	}
	select {
	case <-ctx.Done():
		return ctx.Err()
	case conf, ok := <-b.confirms:
		if !ok {
			b.closeLocked()
			return fmt.Errorf("publisher confirm channel closed")
		}
		if !conf.Ack {
			return fmt.Errorf("broker nacked message")
		}
		return nil
	}
}

func (b *Broker) EnsureUnlocked(ctx context.Context) error {
	if b.pub != nil && !b.pub.IsClosed() && b.conn != nil && !b.conn.IsClosed() {
		return nil
	}
	return b.connectLocked()
}

func (b *Broker) Consume(ctx context.Context, queue string) (<-chan amqp.Delivery, error) {
	conn, err := amqp.DialConfig(b.url, amqp.Config{
		Heartbeat: 10 * time.Second,
		Locale:    "en_US",
	})
	if err != nil {
		return nil, err
	}
	ch, err := conn.Channel()
	if err != nil {
		_ = conn.Close()
		return nil, err
	}
	if err := Declare(ch); err != nil {
		_ = ch.Close()
		_ = conn.Close()
		return nil, err
	}
	if err := ch.Qos(1, 0, false); err != nil {
		_ = ch.Close()
		_ = conn.Close()
		return nil, err
	}
	msgs, err := ch.Consume(queue, "", false, false, false, false, nil)
	if err != nil {
		_ = ch.Close()
		_ = conn.Close()
		return nil, err
	}
	go func() {
		<-ctx.Done()
		_ = ch.Close()
		_ = conn.Close()
	}()
	return msgs, nil
}

func (b *Broker) Close() {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.closeLocked()
}

func (b *Broker) closeLocked() {
	if b.pub != nil {
		_ = b.pub.Close()
		b.pub = nil
	}
	if b.conn != nil {
		_ = b.conn.Close()
		b.conn = nil
	}
	b.confirms = nil
}
