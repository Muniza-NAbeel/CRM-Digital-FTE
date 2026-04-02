"""
Run both API server and Message Worker together.
Single command to start everything!

Usage:
    python run_both.py

This will start:
    1. API Server on http://0.0.0.0:8000
    2. Message Worker (processing emails/WhatsApp responses)
"""
import asyncio
import uvicorn
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def run_api_server():
    """Run FastAPI server."""
    print(f"\n{'='*60}")
    print(f"🚀 Starting API Server on http://0.0.0.0:8000")
    print(f"{'='*60}")

    config = uvicorn.Config(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
        access_log=False,
    )

    server = uvicorn.Server(config)
    
    # Use server.serve() which runs indefinitely
    await server.serve()


async def run_worker():
    """Run message worker."""
    print(f"\n{'='*60}")
    print(f"⚙️  Starting Message Worker...")
    print(f"{'='*60}")
    
    from src.workers.message_worker import get_worker
    
    worker = get_worker()
    await worker.start()
    
    # Keep worker running
    try:
        while True:
            await asyncio.sleep(1)
            
            # Print heartbeat every 30 seconds
            if int(datetime.now().timestamp()) % 30 == 0:
                stats = worker.get_stats()
                print(f"❤️  Worker heartbeat - Processed: {stats['processed_count']}, Errors: {stats['error_count']}")
                
    except asyncio.CancelledError:
        print("\n⏹️  Stopping worker...")
        await worker.stop()
        raise


async def main():
    """Run both API and worker concurrently."""
    print("\n" + "="*60)
    print("🎯 Customer Success FTE - Starting All Services")
    print("="*60)
    print()
    print("Services starting:")
    print("  1. 🌐 API Server (port 8000)")
    print("  2. ⚙️  Message Worker (email/WhatsApp delivery)")
    print()
    print("Press Ctrl+C to stop all services")
    print("="*60)

    # Run both concurrently
    try:
        # Create tasks explicitly
        api_task = asyncio.create_task(run_api_server())
        worker_task = asyncio.create_task(run_worker())
        
        # Wait for both tasks
        await asyncio.gather(api_task, worker_task, return_exceptions=False)
    except asyncio.CancelledError:
        print("\n\n⏹️  Shutting down all services...")
        raise
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ All services stopped successfully!")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
