gateway-metrics.token
  Shared secret for Prometheus -> api-gateway GET /metrics (Bearer token).
  Replace in production; mount the same file into api-gateway (METRICS_SCRAPE_TOKEN_FILE)
  and keep it out of version control if you use real credentials.
