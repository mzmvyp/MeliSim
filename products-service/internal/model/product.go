package model

import "time"

type Product struct {
	ID          int64     `json:"id"`
	SellerID    int64     `json:"seller_id"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	Category    string    `json:"category"`
	Price       float64   `json:"price"`
	Stock       int       `json:"stock"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

type CreateProductRequest struct {
	SellerID    int64   `json:"seller_id"`
	Title       string  `json:"title"`
	Description string  `json:"description"`
	Category    string  `json:"category"`
	Price       float64 `json:"price"`
	Stock       int     `json:"stock"`
}

type UpdateProductRequest struct {
	Title       *string  `json:"title"`
	Description *string  `json:"description"`
	Category    *string  `json:"category"`
	Price       *float64 `json:"price"`
}

type UpdateStockRequest struct {
	Delta int `json:"delta"`
}

type StockUpdatedEvent struct {
	ProductID int64 `json:"product_id"`
	Stock     int   `json:"stock"`
	Delta     int   `json:"delta"`
}

type ProductCreatedEvent struct {
	Product Product `json:"product"`
}
