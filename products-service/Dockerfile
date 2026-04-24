FROM golang:1.22-alpine AS build
WORKDIR /src
RUN apk add --no-cache git
COPY go.mod go.sum* ./
RUN go mod download || true
COPY . .
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/products-service ./cmd

FROM alpine:3.19 AS runtime
RUN apk add --no-cache ca-certificates wget
WORKDIR /app
COPY --from=build /out/products-service /app/products-service
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8002/health | grep -q '"ok"' || exit 1
ENTRYPOINT ["/app/products-service"]
