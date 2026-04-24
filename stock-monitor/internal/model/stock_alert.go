package model

type Product struct {
	ID       int64   `json:"id"`
	SellerID int64   `json:"seller_id"`
	Title    string  `json:"title"`
	Price    float64 `json:"price"`
	Stock    int     `json:"stock"`
	Category string  `json:"category"`
}

type ListResponse struct {
	Items []Product `json:"items"`
	Page  int       `json:"page"`
	Size  int       `json:"size"`
}

type StockAlert struct {
	ProductID int64  `json:"product_id"`
	SellerID  int64  `json:"seller_id"`
	Title     string `json:"title"`
	Stock     int    `json:"stock"`
	Threshold int    `json:"threshold"`
}
