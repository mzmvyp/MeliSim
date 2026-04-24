package observability

import (
	"net/http"
	"strconv"
	"time"

	"github.com/google/uuid"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	requests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Total HTTP requests processed",
	}, []string{"method", "path", "status"})

	latency = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "http_request_duration_seconds",
		Help:    "HTTP request duration",
		Buckets: []float64{.01, .05, .1, .25, .5, 1, 2.5, 5, 10},
	}, []string{"method", "path"})

	EventsPublished = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "melisim_events_published_total",
		Help: "Kafka events published",
	}, []string{"event_type"})
)

func MetricsHandler() http.Handler {
	return promhttp.Handler()
}

// statusRecorder captures the status code for metrics.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(code int) {
	s.status = code
	s.ResponseWriter.WriteHeader(code)
}

// Metrics is an HTTP middleware that records request count + latency.
func Metrics(pathFn func(*http.Request) string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path == "/metrics" {
				next.ServeHTTP(w, r)
				return
			}
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(rec, r)
			path := r.URL.Path
			if pathFn != nil {
				path = pathFn(r)
			}
			latency.WithLabelValues(r.Method, path).Observe(time.Since(start).Seconds())
			requests.WithLabelValues(r.Method, path, strconv.Itoa(rec.status)).Inc()
		})
	}
}

// CorrelationID propagates X-Request-ID or mints a fresh UUID.
func CorrelationID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rid := r.Header.Get("X-Request-ID")
		if rid == "" {
			rid = uuid.NewString()
			r.Header.Set("X-Request-ID", rid)
		}
		w.Header().Set("X-Request-ID", rid)
		next.ServeHTTP(w, r)
	})
}
