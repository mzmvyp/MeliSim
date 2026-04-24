package middleware

import (
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5/middleware"
)

func StructuredLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		ww := middleware.NewWrapResponseWriter(w, r.ProtoMajor)
		next.ServeHTTP(ww, r)
		log.Printf(`{"ts":"%s","level":"INFO","method":"%s","path":"%s","status":%d,"duration_ms":%d}`,
			start.Format(time.RFC3339),
			r.Method, r.URL.Path, ww.Status(), time.Since(start).Milliseconds())
	})
}
