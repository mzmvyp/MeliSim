package monitor

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/melisim/stock-monitor/internal/model"
)

// Client fetches products from the products-service over HTTP.
type Client struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

// FetchAll walks through pages of /products and returns every product.
func (c *Client) FetchAll(ctx context.Context) ([]model.Product, error) {
	all := make([]model.Product, 0, 128)
	const pageSize = 100
	page := 1
	for {
		items, err := c.fetchPage(ctx, page, pageSize)
		if err != nil {
			return nil, err
		}
		if len(items) == 0 {
			break
		}
		all = append(all, items...)
		if len(items) < pageSize {
			break
		}
		page++
	}
	return all, nil
}

func (c *Client) fetchPage(ctx context.Context, page, size int) ([]model.Product, error) {
	url := fmt.Sprintf("%s/products?page=%d&size=%d", c.baseURL, page, size)
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("products-service page=%d status=%d body=%s", page, resp.StatusCode, body)
	}
	var list model.ListResponse
	if err := json.NewDecoder(resp.Body).Decode(&list); err != nil {
		return nil, err
	}
	return list.Items, nil
}

// LowStock filters products whose stock is strictly below threshold.
func LowStock(products []model.Product, threshold int) []model.Product {
	out := make([]model.Product, 0)
	for _, p := range products {
		if p.Stock < threshold {
			out = append(out, p)
		}
	}
	return out
}
