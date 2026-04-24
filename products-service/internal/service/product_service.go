package service

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/melisim/products-service/internal/cache"
	"github.com/melisim/products-service/internal/events"
	"github.com/melisim/products-service/internal/model"
	"github.com/melisim/products-service/internal/repository"
)

var (
	ErrInvalidInput = errors.New("invalid input")
	ErrNotFound     = repository.ErrNotFound
)

const (
	listTTL    = 5 * time.Minute
	productTTL = 5 * time.Minute
)

type Store interface {
	List(ctx context.Context, page, size int) ([]model.Product, error)
	GetByID(ctx context.Context, id int64) (*model.Product, error)
	Create(ctx context.Context, in model.CreateProductRequest) (*model.Product, error)
	Update(ctx context.Context, id int64, in model.UpdateProductRequest) (*model.Product, error)
	Delete(ctx context.Context, id int64) error
	ApplyStockDelta(ctx context.Context, id int64, delta int) (*model.Product, error)
}

type Cache interface {
	GetJSON(ctx context.Context, key string, dst any) error
	SetJSON(ctx context.Context, key string, v any, ttl time.Duration) error
	Del(ctx context.Context, keys ...string)
}

type Service struct {
	store Store
	cache Cache
	pub   events.Publisher
}

func New(store Store, c Cache, pub events.Publisher) *Service {
	return &Service{store: store, cache: c, pub: pub}
}

func listKey(page, size int) string    { return fmt.Sprintf("products:list:p=%d:s=%d", page, size) }
func productKey(id int64) string       { return fmt.Sprintf("products:item:%d", id) }

func (s *Service) List(ctx context.Context, page, size int) ([]model.Product, error) {
	var cached []model.Product
	key := listKey(page, size)
	if s.cache != nil {
		if err := s.cache.GetJSON(ctx, key, &cached); err == nil {
			return cached, nil
		}
	}
	items, err := s.store.List(ctx, page, size)
	if err != nil {
		return nil, err
	}
	if s.cache != nil {
		_ = s.cache.SetJSON(ctx, key, items, listTTL)
	}
	return items, nil
}

func (s *Service) GetByID(ctx context.Context, id int64) (*model.Product, error) {
	if s.cache != nil {
		var p model.Product
		if err := s.cache.GetJSON(ctx, productKey(id), &p); err == nil {
			return &p, nil
		}
	}
	p, err := s.store.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if s.cache != nil {
		_ = s.cache.SetJSON(ctx, productKey(id), p, productTTL)
	}
	return p, nil
}

func (s *Service) Create(ctx context.Context, in model.CreateProductRequest) (*model.Product, error) {
	if err := validateCreate(in); err != nil {
		return nil, err
	}
	p, err := s.store.Create(ctx, in)
	if err != nil {
		return nil, err
	}
	s.invalidate(ctx, 0)
	if s.pub != nil {
		_ = s.pub.Publish(ctx, "product-created", fmt.Sprint(p.ID), model.ProductCreatedEvent{Product: *p})
	}
	return p, nil
}

func (s *Service) Update(ctx context.Context, id int64, in model.UpdateProductRequest) (*model.Product, error) {
	p, err := s.store.Update(ctx, id, in)
	if err != nil {
		return nil, err
	}
	s.invalidate(ctx, id)
	return p, nil
}

func (s *Service) Delete(ctx context.Context, id int64) error {
	if err := s.store.Delete(ctx, id); err != nil {
		return err
	}
	s.invalidate(ctx, id)
	return nil
}

func (s *Service) UpdateStock(ctx context.Context, id int64, delta int) (*model.Product, error) {
	if delta == 0 {
		return nil, fmt.Errorf("%w: delta cannot be zero", ErrInvalidInput)
	}
	p, err := s.store.ApplyStockDelta(ctx, id, delta)
	if err != nil {
		return nil, err
	}
	s.invalidate(ctx, id)
	if s.pub != nil {
		_ = s.pub.Publish(ctx, "stock-updates", fmt.Sprint(p.ID),
			model.StockUpdatedEvent{ProductID: p.ID, Stock: p.Stock, Delta: delta})
	}
	return p, nil
}

func (s *Service) invalidate(ctx context.Context, id int64) {
	if s.cache == nil {
		return
	}
	keys := []string{
		listKey(1, 20), listKey(1, 50), listKey(1, 100),
	}
	if id > 0 {
		keys = append(keys, productKey(id))
	}
	s.cache.Del(ctx, keys...)
}

func validateCreate(in model.CreateProductRequest) error {
	if in.SellerID <= 0 {
		return fmt.Errorf("%w: seller_id is required", ErrInvalidInput)
	}
	if in.Title == "" {
		return fmt.Errorf("%w: title is required", ErrInvalidInput)
	}
	if in.Price < 0 {
		return fmt.Errorf("%w: price must be >= 0", ErrInvalidInput)
	}
	if in.Stock < 0 {
		return fmt.Errorf("%w: stock must be >= 0", ErrInvalidInput)
	}
	return nil
}
