package events

import (
	"context"
	"encoding/json"
	"log"
	"strings"

	"github.com/segmentio/kafka-go"
)

type Publisher interface {
	Publish(ctx context.Context, topic string, key string, value any) error
	Close() error
}

type KafkaPublisher struct {
	brokers []string
	writers map[string]*kafka.Writer
}

func NewKafkaPublisher(brokers string) *KafkaPublisher {
	return &KafkaPublisher{
		brokers: strings.Split(brokers, ","),
		writers: make(map[string]*kafka.Writer),
	}
}

func (p *KafkaPublisher) writer(topic string) *kafka.Writer {
	if w, ok := p.writers[topic]; ok {
		return w
	}
	w := &kafka.Writer{
		Addr:                   kafka.TCP(p.brokers...),
		Topic:                  topic,
		Balancer:               &kafka.Hash{},
		AllowAutoTopicCreation: true,
	}
	p.writers[topic] = w
	return w
}

func (p *KafkaPublisher) Publish(ctx context.Context, topic, key string, value any) error {
	payload, err := json.Marshal(value)
	if err != nil {
		return err
	}
	err = p.writer(topic).WriteMessages(ctx, kafka.Message{
		Key:   []byte(key),
		Value: payload,
	})
	if err != nil {
		// Don't fail the request if Kafka is down — log and move on.
		log.Printf(`{"level":"WARN","msg":"kafka publish failed","topic":"%s","error":"%s"}`, topic, err.Error())
	}
	return nil
}

func (p *KafkaPublisher) Close() error {
	for _, w := range p.writers {
		_ = w.Close()
	}
	return nil
}
