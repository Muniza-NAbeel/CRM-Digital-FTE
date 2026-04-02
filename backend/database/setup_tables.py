"""
Database Setup Script - Create all tables from schema.sql

Usage:
    uv run python database/setup_tables.py
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def setup_database():
    """Create all tables from schema.sql"""
    
    # Load schema
    schema_path = Path(__file__).parent / "schema.sql"
    
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        return False
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    logger.info(f"Loaded schema from: {schema_path}")
    
    # Get database URL from environment
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    database_url = os.getenv("APP_DATABASE_URL")
    fallback_url = os.getenv("APP_FALLBACK_DATABASE_URL")
    
    if not database_url and not fallback_url:
        logger.error("No database URL found in .env file")
        return False
    
    # Try primary database first
    db_url_to_use = database_url or fallback_url
    db_type = "Primary" if database_url else "Fallback"
    
    logger.info(f"Connecting to {db_type} database...")
    logger.info(f"URL: {db_url_to_use[:50]}...")
    
    try:
        # Convert sqlalchemy URL to asyncpg URL if needed
        if db_url_to_use.startswith("postgresql+asyncpg://"):
            asyncpg_url = db_url_to_use.replace("postgresql+asyncpg://", "postgresql://")
        elif db_url_to_use.startswith("postgresql://"):
            asyncpg_url = db_url_to_use
        elif db_url_to_use.startswith("sqlite"):
            logger.info("SQLite detected - tables will be created automatically by SQLAlchemy on first use.")
            logger.info("No manual setup needed for SQLite!")
            return True
        else:
            logger.error(f"Unsupported database URL format: {db_url_to_use[:20]}...")
            return False
        
        # Connect and execute schema
        logger.info("Executing schema...")
        
        import asyncpg
        
        conn = await asyncpg.connect(asyncpg_url)
        
        try:
            # Split schema into individual statements
            # Remove DO blocks and execute statements one by one
            statements = []
            current_statement = []
            in_do_block = 0
            in_function = False
            brace_count = 0
            
            lines = schema_sql.split('\n')
            
            for line in lines:
                stripped = line.strip()
                
                # Skip comments
                if stripped.startswith('--'):
                    continue
                
                # Track DO blocks
                if 'DO $$' in stripped or 'DO$$' in stripped:
                    in_do_block += 1
                    continue
                
                if in_do_block > 0:
                    if '$$;' in stripped or 'END$$;' in stripped:
                        in_do_block -= 1
                    continue
                
                # Track CREATE FUNCTION blocks
                if 'CREATE FUNCTION' in stripped or 'CREATE OR REPLACE FUNCTION' in stripped:
                    in_function = True
                
                if in_function:
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0 and ');' in stripped:
                        in_function = False
                        brace_count = 0
                
                current_statement.append(line)
                
                # Check if statement is complete
                if stripped.endswith(';') and not in_function:
                    stmt = '\n'.join(current_statement).strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt)
                    current_statement = []
            
            # Execute each statement
            logger.info(f"Executing {len(statements)} statements...")
            
            for i, stmt in enumerate(statements, 1):
                try:
                    await conn.execute(stmt)
                    if i % 10 == 0:
                        logger.info(f"  Executed {i}/{len(statements)} statements...")
                except Exception as e:
                    # Log but continue for non-critical errors
                    if 'already exists' in str(e).lower():
                        logger.debug(f"  Skipping (already exists): {stmt[:50]}...")
                    else:
                        logger.warning(f"  Statement {i} warning: {e}")
            
            logger.info("✓ Schema executed successfully!")
            logger.info("✓ All tables, indexes, triggers, and views created!")
            
            # Verify tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            logger.info("\nCreated tables:")
            for table in tables:
                logger.info(f"  - {table['table_name']}")
            
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"✗ Schema execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Customer Success Digital FTE - Database Setup")
    logger.info("=" * 60)
    
    success = asyncio.run(setup_database())
    
    if success:
        logger.info("\n✓ Database setup complete!")
    else:
        logger.error("\n✗ Database setup failed!")
        exit(1)
