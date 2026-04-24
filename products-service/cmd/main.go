package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/melisim/products-service/internal/cache"
	"github.com/melisim/products-service/internal/events"
	"github.com/melisim/products-service/internal/handler"
	mw "github.com/melisim/products-service/internal/middleware"
	"github.com/melisim/products-service/internal/repository"
	"github.com/melisim/products-service/internal/service"
)

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	dbURL := envOr("DATABASE_URL", "postgres://melisim:melisim123@localhost:5432/melisim?sslmode=disable")
	redisURL := envOr("REDIS_URL", "localhost:6379")
	kafkaBrokers := envOr("KAFKA_BROKERS", "localhost:9092")
	port := envOr("PORT", "8002")

	repo, err := repository.New(ctx, dbURL)
	if err != nil {
		log.Fatalf("postgres: %v", err)
	}
	defer repo.Close()

	rc := cache.New(redisURL)
	defer rc.Close()

	publisher := events.NewKafkaPublisher(kafkaBrokers)
	defer publisher.Close()

	svc := service.New(repo, rc, publisher)
	h := handler.New(svc)

	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.Recoverer)
	r.Use(mw.StructuredLogger)

	r.Get("/health", h.Health)
	r.Route("/products", func(r chi.Router) {
		r.Get("/", h.List)
		r.Post("/", h.Create)
		r.Get("/{id}", h.GetByID)
		r.Put("/{id}", h.Update)
		r.Delete("/{id}", h.Delete)
		r.Patch("/{id}/stock", h.UpdateStock)
	})

	srv := &http.Server{
		Addr:              ":" + port,
		Handler:           r,
		ReadHeaderTimeout: 10 * time.Second,
	}

	go func() {
		log.Printf(`{"ts":"%s","level":"INFO","msg":"products-service listening on :%s"}`,
			time.Now().Format(time.RFC3339), port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("server: %v", err)
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
	log.Println("products-service stopped")
}
