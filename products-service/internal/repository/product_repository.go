package repository

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/melisim/products-service/internal/model"
)

var ErrNotFound = errors.New("product not found")

type Repository struct {
	pool *pgxpool.Pool
}

func New(ctx context.Context, dsn string) (*Repository, error) {
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("pgxpool: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("ping: %w", err)
	}
	return &Repository{pool: pool}, nil
}

func (r *Repository) Close() {
	if r.pool != nil {
		r.pool.Close()
	}
}

func (r *Repository) List(ctx context.Context, page, size int) ([]model.Product, error) {
	if page < 1 {
		page = 1
	}
	if size < 1 || size > 200 {
		size = 20
	}
	offset := (page - 1) * size

	rows, err := r.pool.Query(ctx, `
		SELECT id, seller_id, title, COALESCE(description,''), COALESCE(category,''),
		       price, stock, created_at, updated_at
		FROM products
		ORDER BY id DESC
		LIMIT $1 OFFSET $2`, size, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := make([]model.Product, 0, size)
	for rows.Next() {
		var p model.Product
		if err := rows.Scan(&p.ID, &p.SellerID, &p.Title, &p.Description, &p.Category,
			&p.Price, &p.Stock, &p.CreatedAt, &p.UpdatedAt); err != nil {
			return nil, err
		}
		items = append(items, p)
	}
	return items, rows.Err()
}

func (r *Repository) GetByID(ctx context.Context, id int64) (*model.Product, error) {
	var p model.Product
	err := r.pool.QueryRow(ctx, `
		SELECT id, seller_id, title, COALESCE(description,''), COALESCE(category,''),
		       price, stock, created_at, updated_at
		FROM products WHERE id = $1`, id).
		Scan(&p.ID, &p.SellerID, &p.Title, &p.Description, &p.Category,
			&p.Price, &p.Stock, &p.CreatedAt, &p.UpdatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *Repository) Create(ctx context.Context, in model.CreateProductRequest) (*model.Product, error) {
	var p model.Product
	err := r.pool.QueryRow(ctx, `
		INSERT INTO products (seller_id, title, description, category, price, stock)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, seller_id, title, COALESCE(description,''), COALESCE(category,''),
		          price, stock, created_at, updated_at`,
		in.SellerID, in.Title, in.Description, in.Category, in.Price, in.Stock).
		Scan(&p.ID, &p.SellerID, &p.Title, &p.Description, &p.Category,
			&p.Price, &p.Stock, &p.CreatedAt, &p.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *Repository) Update(ctx context.Context, id int64, in model.UpdateProductRequest) (*model.Product, error) {
	existing, err := r.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if in.Title != nil {
		existing.Title = *in.Title
	}
	if in.Description != nil {
		existing.Description = *in.Description
	}
	if in.Category != nil {
		existing.Category = *in.Category
	}
	if in.Price != nil {
		existing.Price = *in.Price
	}

	_, err = r.pool.Exec(ctx, `
		UPDATE products SET title=$1, description=$2, category=$3, price=$4, updated_at=NOW()
		WHERE id=$5`, existing.Title, existing.Description, existing.Category, existing.Price, id)
	if err != nil {
		return nil, err
	}
	return r.GetByID(ctx, id)
}

func (r *Repository) Delete(ctx context.Context, id int64) error {
	ct, err := r.pool.Exec(ctx, `DELETE FROM products WHERE id = $1`, id)
	if err != nil {
		return err
	}
	if ct.RowsAffected() == 0 {
		return ErrNotFound
	}
	return nil
}

// ApplyStockDelta atomically changes stock. Negative delta must not drop stock below zero.
func (r *Repository) ApplyStockDelta(ctx context.Context, id int64, delta int) (*model.Product, error) {
	var p model.Product
	err := r.pool.QueryRow(ctx, `
		UPDATE products
		SET stock = stock + $1, updated_at = NOW()
		WHERE id = $2 AND stock + $1 >= 0
		RETURNING id, seller_id, title, COALESCE(description,''), COALESCE(category,''),
		          price, stock, created_at, updated_at`, delta, id).
		Scan(&p.ID, &p.SellerID, &p.Title, &p.Description, &p.Category,
			&p.Price, &p.Stock, &p.CreatedAt, &p.UpdatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &p, nil
}

// LowStock returns every product with stock below threshold.
func (r *Repository) LowStock(ctx context.Context, threshold int) ([]model.Product, error) {
	rows, err := r.pool.Query(ctx, `
		SELECT id, seller_id, title, COALESCE(description,''), COALESCE(category,''),
		       price, stock, created_at, updated_at
		FROM products
		WHERE stock < $1
		ORDER BY stock ASC, id ASC`, threshold)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	items := make([]model.Product, 0)
	for rows.Next() {
		var p model.Product
		if err := rows.Scan(&p.ID, &p.SellerID, &p.Title, &p.Description, &p.Category,
			&p.Price, &p.Stock, &p.CreatedAt, &p.UpdatedAt); err != nil {
			return nil, err
		}
		items = append(items, p)
	}
	return items, rows.Err()
}
