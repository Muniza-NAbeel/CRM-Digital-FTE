# Customer Success Digital FTE - Backend

All backend code, configuration, and deployment files are located in the `backend/` directory.

## Quick Start

### Running the server

```bash
# Option 1: Use the start script (Windows)
start_server.bat

# Option 2: Manual command
cd backend
..\.venv\Scripts\activate
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Running migrations

```bash
cd backend
..\.venv\Scripts\activate
python apply_migration.py
```

### Docker

```bash
cd backend
docker-compose up -d
```

## Project Structure

```
hackathon_five/
├── backend/           # All backend code and config
│   ├── src/          # Python source code
│   ├── database/     # Database schemas and migrations
│   ├── tests/        # Test files
│   ├── .env          # Environment variables
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── .venv/            # Virtual environment
└── start_server.bat  # Convenience script
```
