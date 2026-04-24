package cache

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/redis/go-redis/v9"
)

var ErrMiss = errors.New("cache miss")

type Cache struct {
	client *redis.Client
}

func New(addr string) *Cache {
	return &Cache{
		client: redis.NewClient(&redis.Options{Addr: addr}),
	}
}

func (c *Cache) Close() error {
	if c.client == nil {
		return nil
	}
	return c.client.Close()
}

func (c *Cache) GetJSON(ctx context.Context, key string, dst any) error {
	b, err := c.client.Get(ctx, key).Bytes()
	if errors.Is(err, redis.Nil) {
		return ErrMiss
	}
	if err != nil {
		return err
	}
	return json.Unmarshal(b, dst)
}

func (c *Cache) SetJSON(ctx context.Context, key string, v any, ttl time.Duration) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return c.client.Set(ctx, key, b, ttl).Err()
}

func (c *Cache) Del(ctx context.Context, keys ...string) {
	if len(keys) == 0 {
		return
	}
	_ = c.client.Del(ctx, keys...).Err()
}
