# Customer Success Digital FTE - Docker Guide

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
# Required: APP_OPENAI_API_KEY
```

### 2. Start All Services

```bash
# Start with default settings
docker-compose up -d

# Or use make
make up
```

### 3. Verify Services

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test API health
curl http://localhost:8000/health/ready
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI application |
| worker | - | Kafka message processor |
| postgres | 5432 | PostgreSQL + pgvector |
| kafka | 9092 | Kafka message broker |
| zookeeper | 2181 | Zookeeper (Kafka dependency) |
| kafka-ui | 8080 | Kafka UI (optional) |

## Common Commands

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Restart a service
docker-compose restart api

# Shell into container
docker-compose exec api bash
docker-compose exec worker bash
docker-compose exec postgres psql -U postgres -d customer_success_fte
```

### Using Make

```bash
make up              # Start all services
make down            # Stop all services
make logs            # View all logs
make shell           # Shell into API
make shell-db        # Shell into database
make build           # Rebuild containers
make clean           # Clean up resources
```

## Profiles

### With Kafka UI

```bash
docker-compose --profile with-ui up -d

# Access UI at http://localhost:8080
```

### With Scheduler

```bash
docker-compose --profile with-scheduler up -d
```

## Database

### Initialize Schema

Schema is automatically initialized on first run from `database/schema.sql`.

### Manual Initialization

```bash
make db-init
```

### Backup

```bash
make db-backup
# Creates backup_YYYYMMDD_HHMMSS.sql
```

### Restore

```bash
make db-restore FILE=backup_20240116_120000.sql
```

### Direct SQL Access

```bash
docker-compose exec postgres psql -U postgres -d customer_success_fte
```

## Kafka

### List Topics

```bash
make kafka-topics
```

### Create Topics (Manual)

```bash
make kafka-create-topics
```

Topics are auto-created when first message is published.

### View Messages

```bash
# Incoming tickets
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fte.tickets.incoming \
  --from-beginning

# Agent events
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic fte.agent.events \
  --from-beginning
```

### Kafka UI

```bash
# Start with UI profile
docker-compose --profile with-ui up -d

# Access at http://localhost:8080
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `APP_OPENAI_API_KEY` | OpenAI API key |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DB_PASSWORD` | `postgres` | Database password |
| `APP_SECRET_KEY` | `change-me` | Secret key for security |
| `APP_LOG_LEVEL` | `INFO` | Logging level |
| `APP_LOG_FORMAT` | `text` | `json` or `text` |
| `APP_TWILIO_*` | - | Twilio credentials |
| `APP_GMAIL_*` | - | Gmail API credentials |

## Networking

All services communicate via `fte-network` bridge network.

```
┌─────────────────────────────────────────────────────┐
│                  fte-network                        │
│                                                     │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐        │
│  │   api   │───▶│ postgres│    │  kafka  │        │
│  │ :8000   │    │  :5432  │    │  :9092  │        │
│  └────┬────┘    └─────────┘    └────┬────┘        │
│       │                             │              │
│  ┌────▼────┐    ┌─────────┐        │              │
│  │ worker  │───▶│ postgres│        │              │
│  │         │    │         │        │              │
│  └─────────┘    └─────────┘    ┌───▼────┐        │
│                                 │zookeeper│        │
│                                 │ :2181   │        │
│                                 └─────────┘        │
└─────────────────────────────────────────────────────┘
```

## Health Checks

```bash
# API health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Database health
docker-compose exec postgres pg_isready

# Kafka health
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker-compose logs api

# Verify database is ready
docker-compose logs postgres

# Check environment
docker-compose exec api env | grep APP_
```

### Worker Won't Process Messages

```bash
# Check worker logs
docker-compose logs worker

# Verify Kafka topics exist
make kafka-topics

# Check database connection
docker-compose exec worker python -c "from src.database import get_db_pool; import asyncio; asyncio.run(get_db_pool())"
```

### Database Connection Issues

```bash
# Test connection from API
docker-compose exec api python -c "from src.database import health_check; import asyncio; print(asyncio.run(health_check()))"

# Check PostgreSQL is accepting connections
docker-compose exec postgres pg_isready -U postgres
```

### Kafka Connection Issues

```bash
# Test Kafka connection
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Check Zookeeper
docker-compose logs zookeeper
```

## Production Deployment

### Build for Production

```bash
# Set production target
export DOCKER_TARGET=production

# Build
docker-compose build
```

### Environment Variables for Production

```bash
# .env production
APP_APP_ENV=production
APP_APP_DEBUG=false
APP_SECRET_KEY=<secure-random-key>
APP_DB_PASSWORD=<secure-password>
APP_LOG_FORMAT=json
APP_LOG_LEVEL=WARNING
```

### Resource Limits (docker-compose.override.yml)

```yaml
version: '3.8'

services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  worker:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## Cleanup

### Remove All Data

```bash
# Stop and remove everything
make clean-all

# Or manually
docker-compose down -v --remove-orphans
docker volume rm fte-postgres-data fte-zookeeper-data fte-kafka-data
docker network rm fte-network
```

### Prune Docker Resources

```bash
docker system prune -a --volumes
```
