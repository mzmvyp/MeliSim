package alerter

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/segmentio/kafka-go"

	"github.com/melisim/stock-monitor/internal/model"
)

type Alerter struct {
	writer *kafka.Writer
}

func New(brokers string) *Alerter {
	return &Alerter{
		writer: &kafka.Writer{
			Addr:                   kafka.TCP(strings.Split(brokers, ",")...),
			Topic:                  "stock-alert",
			Balancer:               &kafka.Hash{},
			AllowAutoTopicCreation: true,
		},
	}
}

func (a *Alerter) Close() error {
	if a.writer != nil {
		return a.writer.Close()
	}
	return nil
}

// Publish sends a stock-alert event to Kafka. Logs and swallows errors so a
// kafka outage doesn't crash the monitor.
func (a *Alerter) Publish(ctx context.Context, alert model.StockAlert) {
	payload, err := json.Marshal(alert)
	if err != nil {
		log.Printf(`{"level":"ERROR","msg":"marshal stock alert","error":"%s"}`, err)
		return
	}
	err = a.writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(fmt.Sprint(alert.ProductID)),
		Value: payload,
	})
	if err != nil {
		log.Printf(`{"level":"WARN","msg":"kafka publish failed","error":"%s"}`, err)
	}
}

// LogAudit writes a structured audit line: error_code,YYYY-MM-DD,server_id,endpoint
// (format inspired by the HackerRank Q13 "aggregate errors" challenge).
func LogAudit(serverID, endpoint string, when time.Time, alertCount int) {
	if alertCount == 0 {
		return
	}
	fmt.Printf("ERR_LOW_STOCK,%s,%s,%s\n",
		when.Format("2006-01-02"),
		serverID,
		endpoint,
	)
}
