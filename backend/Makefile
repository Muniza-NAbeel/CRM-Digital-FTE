# Customer Success Digital FTE - Makefile
# Common Docker and development commands

.PHONY: help build up down logs shell worker scheduler test clean

# ============================================================================
# Docker Commands
# ============================================================================

## Build all containers
build:
	docker-compose build

## Build with no cache (fresh build)
build-no-cache:
	docker-compose build --no-cache

## Build API only
build-api:
	docker-compose build api

## Build worker only
build-worker:
	docker-compose build worker

## Start all services
up:
	docker-compose up -d

## Start with UI (Kafka UI)
up-ui:
	docker-compose --profile with-ui up -d

## Start with scheduler
up-scheduler:
	docker-compose --profile with-scheduler up -d

## Start in foreground (development)
dev:
	docker-compose up

## Stop all services
down:
	docker-compose down

## Stop and remove volumes (WARNING: deletes data)
down-volumes:
	docker-compose down -v

## Restart all services
restart:
	docker-compose restart

## View logs
logs:
	docker-compose logs -f

## View API logs only
logs-api:
	docker-compose logs -f api

## View worker logs only
logs-worker:
	docker-compose logs -f worker

## Shell into API container
shell:
	docker-compose exec api bash

## Shell into worker container
shell-worker:
	docker-compose exec worker bash

## Shell into database
shell-db:
	docker-compose exec postgres psql -U postgres -d customer_success_fte

# ============================================================================
# Database Commands
# ============================================================================

## Initialize database schema
db-init:
	docker-compose exec postgres psql -U postgres -d customer_success_fte -f /docker-entrypoint-initdb.d/01-schema.sql

## Backup database
db-backup:
	docker-compose exec postgres pg_dump -U postgres customer_success_fte > backup_$$(date +%Y%m%d_%H%M%S).sql

## Restore database from backup
db-restore:
	@echo "Usage: make db-restore FILE=backup_20240116_120000.sql"
	docker-compose exec -T postgres psql -U postgres customer_success_fte < $(FILE)

## View database size
db-size:
	docker-compose exec postgres psql -U postgres -d customer_success_fte -c "SELECT pg_size_pretty(pg_database_size('customer_success_fte'));"

# ============================================================================
# Kafka Commands
# ============================================================================

## List Kafka topics
kafka-topics:
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

## Create Kafka topics
kafka-create-topics:
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic fte.tickets.incoming --partitions 6 --replication-factor 1
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic fte.tickets.outgoing --partitions 6 --replication-factor 1
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic fte.agent.events --partitions 3 --replication-factor 1
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic fte.dlq --partitions 3 --replication-factor 1
	docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic fte.metrics --partitions 3 --replication-factor 1

## View Kafka topic messages
kafka-consume:
	docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic fte.tickets.incoming --from-beginning

# ============================================================================
# Testing Commands
# ============================================================================

## Run tests
test:
	docker-compose exec api pytest

## Run tests with coverage
test-cov:
	docker-compose exec api pytest --cov=src --cov-report=html

## Run tests verbose
test-v:
	docker-compose exec api pytest -v

# ============================================================================
# Development Commands
# ============================================================================

## Install pre-commit hooks
install-hooks:
	pip install pre-commit
	pre-commit install

## Format code
format:
	black src/ tests/
	isort src/ tests/

## Lint code
lint:
	flake8 src/ tests/
	mypy src/

## Check dependencies
check-deps:
	pip check

## Show environment
env:
	docker-compose config

# ============================================================================
# Cleanup
# ============================================================================

## Clean up Docker resources
clean:
	docker-compose down -v
	docker system prune -f

## Remove all FTE containers and volumes
clean-all:
	docker-compose down -v --remove-orphans
	docker volume rm -f fte-postgres-data fte-zookeeper-data fte-kafka-data
	docker network rm fte-network

# ============================================================================
# Help
# ============================================================================

help:
	@echo "Customer Success Digital FTE - Makefile Commands"
	@echo ""
	@echo "Docker:"
	@echo "  make build          - Build all containers"
	@echo "  make up             - Start all services"
	@echo "  make up-ui          - Start with Kafka UI"
	@echo "  make down           - Stop all services"
	@echo "  make logs           - View logs"
	@echo "  make shell          - Shell into API container"
	@echo ""
	@echo "Database:"
	@echo "  make db-init        - Initialize schema"
	@echo "  make db-backup      - Backup database"
	@echo "  make db-restore     - Restore from backup"
	@echo "  make shell-db       - Shell into database"
	@echo ""
	@echo "Kafka:"
	@echo "  make kafka-topics        - List topics"
	@echo "  make kafka-create-topics - Create topics"
	@echo "  make kafka-consume       - Consume messages"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run tests"
	@echo "  make test-cov       - Run tests with coverage"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          - Clean Docker resources"
	@echo "  make clean-all      - Remove all containers and volumes"
