package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/go-chi/chi/v5"

	"github.com/melisim/products-service/internal/handler"
	"github.com/melisim/products-service/internal/model"
	"github.com/melisim/products-service/internal/service"
)

type fakeSvc struct {
	listFn    func(ctx context.Context, page, size int) ([]model.Product, error)
	getFn     func(ctx context.Context, id int64) (*model.Product, error)
	createFn  func(ctx context.Context, in model.CreateProductRequest) (*model.Product, error)
	updateFn  func(ctx context.Context, id int64, in model.UpdateProductRequest) (*model.Product, error)
	deleteFn  func(ctx context.Context, id int64) error
	stockFn   func(ctx context.Context, id int64, delta int) (*model.Product, error)
}

func (f *fakeSvc) List(ctx context.Context, page, size int) ([]model.Product, error) {
	return f.listFn(ctx, page, size)
}
func (f *fakeSvc) GetByID(ctx context.Context, id int64) (*model.Product, error) {
	return f.getFn(ctx, id)
}
func (f *fakeSvc) Create(ctx context.Context, in model.CreateProductRequest) (*model.Product, error) {
	return f.createFn(ctx, in)
}
func (f *fakeSvc) Update(ctx context.Context, id int64, in model.UpdateProductRequest) (*model.Product, error) {
	return f.updateFn(ctx, id, in)
}
func (f *fakeSvc) Delete(ctx context.Context, id int64) error {
	return f.deleteFn(ctx, id)
}
func (f *fakeSvc) UpdateStock(ctx context.Context, id int64, delta int) (*model.Product, error) {
	return f.stockFn(ctx, id, delta)
}

func newRouter(h *handler.Handler) http.Handler {
	r := chi.NewRouter()
	r.Get("/products", h.List)
	r.Post("/products", h.Create)
	r.Get("/products/{id}", h.GetByID)
	r.Patch("/products/{id}/stock", h.UpdateStock)
	return r
}

func TestCreateProductSuccess(t *testing.T) {
	fake := &fakeSvc{
		createFn: func(_ context.Context, in model.CreateProductRequest) (*model.Product, error) {
			return &model.Product{
				ID: 1, SellerID: in.SellerID, Title: in.Title, Price: in.Price,
				Stock: in.Stock, CreatedAt: time.Now(), UpdatedAt: time.Now(),
			}, nil
		},
	}
	rt := newRouter(handler.New(fake))

	body, _ := json.Marshal(model.CreateProductRequest{
		SellerID: 1, Title: "Book", Price: 99.9, Stock: 5,
	})
	req := httptest.NewRequest(http.MethodPost, "/products", bytes.NewReader(body))
	rec := httptest.NewRecorder()
	rt.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var out model.Product
	_ = json.Unmarshal(rec.Body.Bytes(), &out)
	if out.Title != "Book" {
		t.Fatalf("unexpected body: %+v", out)
	}
}

func TestCreateProductInvalid(t *testing.T) {
	fake := &fakeSvc{
		createFn: func(_ context.Context, _ model.CreateProductRequest) (*model.Product, error) {
			return nil, service.ErrInvalidInput
		},
	}
	rt := newRouter(handler.New(fake))

	req := httptest.NewRequest(http.MethodPost, "/products", bytes.NewReader([]byte(`{}`)))
	rec := httptest.NewRecorder()
	rt.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}

func TestGetProductNotFound(t *testing.T) {
	fake := &fakeSvc{
		getFn: func(_ context.Context, _ int64) (*model.Product, error) {
			return nil, service.ErrNotFound
		},
	}
	rt := newRouter(handler.New(fake))

	req := httptest.NewRequest(http.MethodGet, "/products/999", nil)
	rec := httptest.NewRecorder()
	rt.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func TestUpdateStockRejectsNegativeResult(t *testing.T) {
	fake := &fakeSvc{
		stockFn: func(_ context.Context, _ int64, _ int) (*model.Product, error) {
			return nil, errors.New("stock would go negative")
		},
	}
	rt := newRouter(handler.New(fake))

	body, _ := json.Marshal(model.UpdateStockRequest{Delta: -100})
	req := httptest.NewRequest(http.MethodPatch, "/products/1/stock", bytes.NewReader(body))
	rec := httptest.NewRecorder()
	rt.ServeHTTP(rec, req)

	if rec.Code != http.StatusConflict {
		t.Fatalf("expected 409, got %d", rec.Code)
	}
}

func TestListEmpty(t *testing.T) {
	fake := &fakeSvc{
		listFn: func(_ context.Context, _, _ int) ([]model.Product, error) {
			return []model.Product{}, nil
		},
	}
	rt := newRouter(handler.New(fake))

	req := httptest.NewRequest(http.MethodGet, "/products?page=1&size=20", nil)
	rec := httptest.NewRecorder()
	rt.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}
