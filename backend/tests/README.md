# Customer Success Digital FTE - Test Guide

## Test Structure

```
tests/
├── __init__.py           # Test package
├── conftest.py           # Pytest fixtures and configuration
├── test_e2e.py           # End-to-end tests
├── test_edge_cases.py    # Edge case tests
├── test_load.py          # Load testing (Locust)
└── test_unit.py          # Unit tests
```

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-httpx locust
```

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test type
pytest -m unit       # Unit tests
pytest -m e2e        # E2E tests
pytest -m edge       # Edge case tests
```

## Test Types

### 1. Unit Tests (`test_unit.py`)

Test individual components in isolation.

```bash
# Run unit tests
pytest tests/test_unit.py -v

# Run specific test class
pytest tests/test_unit.py::TestEscalationTriggers -v
```

**Coverage:**
- State transition validation
- Escalation trigger detection
- Channel handler normalization
- Input validation (Pydantic)
- Metrics collection

### 2. End-to-End Tests (`test_e2e.py`)

Test complete user journeys across all channels.

```bash
# Run E2E tests
pytest tests/test_e2e.py -v

# Run specific channel tests
pytest tests/test_e2e.py::TestWebFormE2E -v
pytest tests/test_e2e.py::TestGmailE2E -v
pytest tests/test_e2e.py::TestWhatsAppE2E -v
```

**Coverage:**
- Web Form → Agent → Response
- Gmail → Agent → Response
- WhatsApp → Agent → Response
- Cross-channel continuity
- Customer history tracking

### 3. Edge Case Tests (`test_edge_cases.py`)

Test edge cases and error conditions.

```bash
# Run edge case tests
pytest tests/test_edge_cases.py -v

# Run specific edge case categories
pytest tests/test_edge_cases.py::TestInputValidation -v
pytest tests/test_edge_cases.py::TestSentimentEscalation -v
pytest tests/test_edge_cases.py::TestTopicEscalation -v
```

**Coverage:**
- Empty input handling
- Very long messages
- Special characters / Unicode
- Angry customer escalation
- Pricing/refund/legal escalation
- Rate limiting
- System resilience

### 4. Load Tests (`test_load.py`)

Performance and load testing using Locust.

```bash
# Start Locust web UI
locust -f tests/test_load.py --host=http://localhost:8000

# Open browser to http://localhost:8089

# Run headless (no UI)
locust -f tests/test_load.py \
    --host=http://localhost:8000 \
    --headless \
    -u 100 \
    -r 10 \
    --run-time 5m

# Run from Python
python -c "from tests.test_load import run_load_test; run_load_test(users=50)"
```

**User Classes:**
- `WebFormUser` - Standard web form submissions
- `AngryCustomerUser` - Escalation-triggering messages
- `APIPollerUser` - Ticket status polling
- `MixedChannelUser` - Multi-channel simulation
- `StressTestUser` - High-intensity stress testing

**Performance Thresholds:**
- Avg response time < 1000ms
- Failure rate < 5%
- Minimum 10 RPS

## Test Fixtures

### Database Fixtures

```python
@pytest_asyncio.fixture
async def db_connection(db_pool: Pool) -> AsyncGenerator[Connection, None]:
    """Get a database connection from the pool."""
```

### API Client Fixtures

```python
@pytest_asyncio.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for API testing."""
```

### Test Data Fixtures

```python
@pytest.fixture
def test_customer_data() -> dict:
    """Generate test customer data."""

@pytest.fixture
def test_ticket_data() -> dict:
    """Generate test ticket data."""

@pytest.fixture
def angry_customer_message() -> str:
    """Angry customer message for testing escalation."""

@pytest.fixture
def pricing_query_message() -> str:
    """Pricing-related query that should trigger escalation."""
```

## Environment Variables

```bash
# Test database
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=customer_success_fte_test
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres

# Test API
export TEST_API_URL=http://localhost:8000

# Test Kafka
export TEST_KAFKA_BOOTSTRAP=localhost:9092
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: customer_success_fte_test
        ports:
          - 5432:5432
      
      kafka:
        image: confluentinc/cp-kafka:7.5.0
        env:
          KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
          KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
        ports:
          - 9092:9092
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov locust
      
      - name: Run unit tests
        run: pytest tests/test_unit.py -v --cov=src
      
      - name: Run E2E tests
        run: pytest tests/test_e2e.py -v
      
      - name: Run edge case tests
        run: pytest tests/test_edge_cases.py -v
      
      - name: Run load test (smoke)
        run: |
          locust -f tests/test_load.py \
            --host=http://localhost:8000 \
            --headless \
            -u 20 \
            -r 5 \
            --run-time 1m
```

## Test Reports

### Generate HTML Report

```bash
pytest --html=report.html --self-contained-html
```

### Generate Coverage Report

```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

### Generate JUnit XML (for CI)

```bash
pytest --junitxml=test-results.xml
```

## Performance Benchmarks

| Test Type | Target | Acceptable |
|-----------|--------|------------|
| Unit Tests | < 5s | < 30s |
| E2E Tests | < 30s | < 2m |
| Edge Cases | < 30s | < 2m |
| Load Test (50 users) | < 5m | < 10m |
| API Response Time | < 500ms | < 1000ms |
| Load Test RPS | > 50 | > 20 |

## Troubleshooting

### Database Connection Failed

```bash
# Check test database exists
psql -U postgres -c "CREATE DATABASE customer_success_fte_test;"

# Run migrations
psql -U postgres -d customer_success_fte_test -f database/schema.sql
```

### Kafka Connection Failed

```bash
# Check Kafka is running
docker ps | grep kafka

# Test connection
kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Tests Timing Out

```bash
# Increase timeout
pytest --timeout=60

# Run tests individually to identify slow tests
pytest tests/test_e2e.py -v --durations=0
```

### Load Test Issues

```bash
# Check API is accessible
curl http://localhost:8000/health/ready

# Run with fewer users
locust -f tests/test_load.py --host=http://localhost:8000 -u 10 -r 2
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Mocking**: Mock external dependencies (OpenAI, Twilio)
4. **Async**: Use `@pytest.mark.asyncio` for async tests
5. **Markers**: Use markers to categorize tests
6. **Cleanup**: Clean up test data after tests

## Test Data Management

```python
# Use unique IDs to avoid conflicts
unique_id = str(uuid4())[:8]
email = f"test_{unique_id}@example.com"

# Clean up after tests
@pytest.fixture
def clean_db(db_pool):
    # Clean before
    yield db_pool
    # Clean after
```

## Running in Docker

```bash
# Run tests in container
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=src
```
