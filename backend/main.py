"""
Customer Success Digital FTE - Main Entry Point

Run with:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Production:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from src.api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
