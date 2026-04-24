FROM golang:1.22-alpine AS build
WORKDIR /src
RUN apk add --no-cache git
COPY go.mod go.sum* ./
RUN go mod download || true
COPY . .
RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/stock-monitor ./cmd

FROM alpine:3.19 AS runtime
RUN apk add --no-cache ca-certificates wget
WORKDIR /app
COPY --from=build /out/stock-monitor /app/stock-monitor
EXPOSE 8099
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8099/health | grep -q '"ok"' || exit 1
ENTRYPOINT ["/app/stock-monitor"]
