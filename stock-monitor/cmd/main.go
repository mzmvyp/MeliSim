package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/melisim/stock-monitor/internal/alerter"
	"github.com/melisim/stock-monitor/internal/model"
	"github.com/melisim/stock-monitor/internal/monitor"
)

var (
	ticksTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "melisim_stock_checks_total",
		Help: "Total stock-check ticks executed",
	})
	lastAlerts = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "melisim_stock_low_count",
		Help: "Low-stock products in the last run",
	})
	alertsPublished = promauto.NewCounter(prometheus.CounterOpts{
		Name: "melisim_events_published_total",
		Help: "Events published (here: stock-alert)",
	})
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
	metricsPort := envOr("METRICS_PORT", "8099")

	client := monitor.NewClient(baseURL)
	al := alerter.New(brokers)
	defer al.Close()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// Expose /metrics + /health so Prometheus can scrape and compose can probe.
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok","service":"stock-monitor"}`))
	})
	srv := &http.Server{Addr: ":" + metricsPort, Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf(`{"level":"WARN","msg":"metrics server stopped","error":"%s"}`, err)
		}
	}()

	log.Printf(`{"level":"INFO","msg":"stock-monitor started","interval":"%s","threshold":%d,"metrics_port":"%s"}`,
		interval, threshold, metricsPort)

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	runOnce(ctx, client, al, threshold, serverID)
	for {
		select {
		case <-ctx.Done():
			log.Println(`{"level":"INFO","msg":"stock-monitor stopping"}`)
			shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			_ = srv.Shutdown(shutdownCtx)
			cancel()
			return
		case <-ticker.C:
			runOnce(ctx, client, al, threshold, serverID)
		}
	}
}

func runOnce(ctx context.Context, client *monitor.Client, al *alerter.Alerter, threshold int, serverID string) {
	ticksTotal.Inc()
	products, err := client.FetchAll(ctx)
	if err != nil {
		log.Printf(`{"level":"WARN","msg":"fetch products failed","error":"%s"}`, err)
		return
	}
	low := monitor.LowStock(products, threshold)
	lastAlerts.Set(float64(len(low)))
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
		alertsPublished.Inc()
	}
}
