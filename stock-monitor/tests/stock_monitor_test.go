package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/melisim/stock-monitor/internal/model"
	"github.com/melisim/stock-monitor/internal/monitor"
)

func TestLowStockFiltersByThreshold(t *testing.T) {
	products := []model.Product{
		{ID: 1, Stock: 5},
		{ID: 2, Stock: 15},
		{ID: 3, Stock: 9},
		{ID: 4, Stock: 10}, // exactly at threshold — NOT low
	}
	low := monitor.LowStock(products, 10)
	if len(low) != 2 {
		t.Fatalf("expected 2 low-stock, got %d", len(low))
	}
	ids := map[int64]bool{}
	for _, p := range low {
		ids[p.ID] = true
	}
	if !ids[1] || !ids[3] {
		t.Fatalf("unexpected low-stock ids: %v", ids)
	}
}

func TestLowStockEmptyInput(t *testing.T) {
	if got := monitor.LowStock(nil, 10); len(got) != 0 {
		t.Fatalf("expected 0 items, got %d", len(got))
	}
}

func TestFetchAllPaginates(t *testing.T) {
	page1 := model.ListResponse{Page: 1, Size: 100, Items: make([]model.Product, 100)}
	for i := range page1.Items {
		page1.Items[i] = model.Product{ID: int64(i + 1), Stock: 50}
	}
	page2 := model.ListResponse{Page: 2, Size: 100, Items: []model.Product{{ID: 101, Stock: 1}}}

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Query().Get("page") == "1" {
			_ = json.NewEncoder(w).Encode(page1)
			return
		}
		_ = json.NewEncoder(w).Encode(page2)
	}))
	defer srv.Close()

	client := monitor.NewClient(srv.URL)
	all, err := client.FetchAll(context.Background())
	if err != nil {
		t.Fatalf("FetchAll error: %v", err)
	}
	if len(all) != 101 {
		t.Fatalf("expected 101 products across pages, got %d", len(all))
	}
	if all[100].ID != 101 {
		t.Fatalf("last id should be 101, got %d", all[100].ID)
	}
}

func TestFetchAllStopsOnEmpty(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(model.ListResponse{Items: []model.Product{}})
	}))
	defer srv.Close()

	client := monitor.NewClient(srv.URL)
	all, err := client.FetchAll(context.Background())
	if err != nil {
		t.Fatalf("FetchAll error: %v", err)
	}
	if len(all) != 0 {
		t.Fatalf("expected 0 items, got %d", len(all))
	}
}
