package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/melisim/stock-monitor/internal/alerter"
	"github.com/melisim/stock-monitor/internal/model"
	"github.com/melisim/stock-monitor/internal/monitor"
)

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		n, err := strconv.Atoi(v)
		if err == nil {
			return n
		}
	}
	return def
}

func main() {
	baseURL := envOr("PRODUCTS_SERVICE_URL", "http://localhost:8002")
	brokers := envOr("KAFKA_BROKERS", "localhost:9092")
	interval := time.Duration(envInt("CHECK_INTERVAL_SECONDS", 60)) * time.Second
	threshold := envInt("STOCK_THRESHOLD", 10)
	serverID := envOr("SERVER_ID", "stock-monitor-1")

	client := monitor.NewClient(baseURL)
	al := alerter.New(brokers)
	defer al.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	log.Printf(`{"level":"INFO","msg":"stock-monitor started","interval":"%s","threshold":%d}`, interval, threshold)

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	runOnce(ctx, client, al, threshold, serverID)
	for {
		select {
		case <-ctx.Done():
			log.Println(`{"level":"INFO","msg":"stock-monitor stopping"}`)
			return
		case <-ticker.C:
			runOnce(ctx, client, al, threshold, serverID)
		}
	}
}

func runOnce(ctx context.Context, client *monitor.Client, al *alerter.Alerter, threshold int, serverID string) {
	products, err := client.FetchAll(ctx)
	if err != nil {
		log.Printf(`{"level":"WARN","msg":"fetch products failed","error":"%s"}`, err)
		return
	}
	low := monitor.LowStock(products, threshold)
	log.Printf(`{"level":"INFO","msg":"stock check","checked":%d,"low":%d}`, len(products), len(low))

	alerter.LogAudit(serverID, "/products", time.Now(), len(low))

	for _, p := range low {
		al.Publish(ctx, model.StockAlert{
			ProductID: p.ID,
			SellerID:  p.SellerID,
			Title:     p.Title,
			Stock:     p.Stock,
			Threshold: threshold,
		})
	}
}
