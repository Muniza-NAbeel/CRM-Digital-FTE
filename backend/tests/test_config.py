"""
Comprehensive Test Script - Verify All Configurations

Usage:
    uv run python tests/test_config.py
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("CUSTOM SUCCESS DIGITAL FTE - CONFIGURATION TEST")
print("=" * 60)

all_passed = True

# ============================================================================
# 1. Environment Variables
# ============================================================================
print("\n1. ENVIRONMENT VARIABLES")
print("-" * 40)

required_vars = {
    "APP_APP_ENV": "Application Environment",
    "APP_SECRET_KEY": "Secret Key",
    "APP_DATABASE_URL": "Database URL",
    "APP_OPENAI_API_KEY": "OpenAI API Key",
    "APP_GMAIL_CLIENT_ID": "Gmail Client ID",
    "APP_GMAIL_CLIENT_SECRET": "Gmail Client Secret",
    "APP_GMAIL_REFRESH_TOKEN": "Gmail Refresh Token",
    "APP_TWILIO_ACCOUNT_SID": "Twilio Account SID",
    "APP_TWILIO_AUTH_TOKEN": "Twilio Auth Token",
}

for var, description in required_vars.items():
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "KEY" in var or "TOKEN" in var or "SECRET" in var:
            masked = value[:10] + "..." + value[-5:] if len(value) > 15 else "***"
        else:
            masked = value
        print(f"  ✓ {description}: {masked}")
    else:
        print(f"  ✗ {description}: MISSING")
        all_passed = False

# ============================================================================
# 2. Database Configuration
# ============================================================================
print("\n2. DATABASE CONFIGURATION")
print("-" * 40)

db_url = os.getenv("APP_DATABASE_URL")
fallback_url = os.getenv("APP_FALLBACK_DATABASE_URL")

if db_url and db_url.startswith("postgresql+asyncpg://"):
    print(f"  ✓ Primary Database: PostgreSQL (async)")
    # Extract host (mask credentials)
    if "neon.tech" in db_url:
        print(f"  ✓ Provider: Neon (Cloud)")
    elif "localhost" in db_url:
        print(f"  ✓ Provider: Local PostgreSQL")
    else:
        print(f"  ✓ Provider: Remote PostgreSQL")
else:
    print(f"  ✗ Primary Database: Invalid URL format")
    all_passed = False

if fallback_url and fallback_url.startswith("sqlite+aiosqlite://"):
    print(f"  ✓ Fallback Database: SQLite")
else:
    print(f"  ✗ Fallback Database: Not configured")
    all_passed = False

# ============================================================================
# 3. OpenAI Configuration
# ============================================================================
print("\n3. OPENAI CONFIGURATION")
print("-" * 40)

openai_key = os.getenv("APP_OPENAI_API_KEY")
openai_model = os.getenv("APP_OPENAI_MODEL", "gpt-4")
openai_embedding = os.getenv("APP_OPENAI_EMBEDDING_MODEL")

if openai_key and openai_key.startswith("sk-"):
    print(f"  ✓ API Key: Configured ({openai_key[:15]}...)")
    print(f"  ✓ Model: {openai_model}")
    print(f"  ✓ Embedding Model: {openai_embedding}")
else:
    print(f"  ✗ API Key: Invalid or missing")
    all_passed = False

# ============================================================================
# 4. Gmail Configuration
# ============================================================================
print("\n4. GMAIL API CONFIGURATION")
print("-" * 40)

gmail_client = os.getenv("APP_GMAIL_CLIENT_ID")
gmail_secret = os.getenv("APP_GMAIL_CLIENT_SECRET")
gmail_refresh = os.getenv("APP_GMAIL_REFRESH_TOKEN")

if gmail_client and gmail_client.endswith("apps.googleusercontent.com"):
    print(f"  ✓ Client ID: Configured")
else:
    print(f"  ✗ Client ID: Invalid")
    all_passed = False

if gmail_secret and gmail_secret.startswith("GOCSPX-"):
    print(f"  ✓ Client Secret: Configured")
else:
    print(f"  ✗ Client Secret: Invalid")
    all_passed = False

if gmail_refresh and gmail_refresh.startswith("1//"):
    print(f"  ✓ Refresh Token: Configured")
else:
    print(f"  ✗ Refresh Token: Invalid")
    all_passed = False

# ============================================================================
# 5. Twilio Configuration
# ============================================================================
print("\n5. TWILIO (WHATSAPP) CONFIGURATION")
print("-" * 40)

twilio_sid = os.getenv("APP_TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("APP_TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("APP_TWILIO_WHATSAPP_NUMBER")

if twilio_sid and twilio_sid.startswith("AC"):
    print(f"  ✓ Account SID: Configured")
else:
    print(f"  ✗ Account SID: Invalid")
    all_passed = False

if twilio_token and len(twilio_token) == 32:
    print(f"  ✓ Auth Token: Configured")
else:
    print(f"  ✗ Auth Token: Invalid length")
    all_passed = False

if twilio_number and twilio_number.startswith("whatsapp:+"):
    print(f"  ✓ WhatsApp Number: {twilio_number}")
else:
    print(f"  ✗ WhatsApp Number: Invalid format")
    all_passed = False

# ============================================================================
# 6. Security Configuration
# ============================================================================
print("\n6. SECURITY CONFIGURATION")
print("-" * 40)

secret_key = os.getenv("APP_SECRET_KEY")
cors_origins = os.getenv("APP_CORS_ORIGINS")

if secret_key and len(secret_key) >= 32:
    print(f"  ✓ Secret Key: {len(secret_key)} characters (secure)")
else:
    print(f"  ✗ Secret Key: Too short (min 32 chars)")
    all_passed = False

if cors_origins:
    print(f"  ✓ CORS Origins: {cors_origins}")
else:
    print(f"  ✗ CORS Origins: Not configured")
    all_passed = False

# ============================================================================
# 7. Feature Flags
# ============================================================================
print("\n7. FEATURE FLAGS")
print("-" * 40)

features = {
    "APP_ENABLE_SENTIMENT_ANALYSIS": "Sentiment Analysis",
    "APP_ENABLE_AUTO_ESCALATION": "Auto Escalation",
    "APP_ENABLE_KNOWLEDGE_BASE_LEARNING": "Knowledge Base Learning",
    "APP_ENABLE_METRICS_COLLECTION": "Metrics Collection",
}

for var, name in features.items():
    value = os.getenv(var, "false").lower()
    status = "Enabled" if value == "true" else "Disabled"
    print(f"  {'✓' if value == 'true' else '○'} {name}: {status}")

# ============================================================================
# 8. Database Tables Check
# ============================================================================
print("\n8. DATABASE TABLES CHECK")
print("-" * 40)

async def check_tables():
    try:
        import asyncpg
        
        db_url = os.getenv("APP_DATABASE_URL")
        if db_url:
            asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            conn = await asyncpg.connect(asyncpg_url)
            
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            expected_tables = [
                "customers", "tickets", "conversations", "messages",
                "knowledge_base", "customer_identifiers", "channel_configs",
                "agent_metrics"
            ]
            
            table_names = [t["table_name"] for t in tables]
            
            for table in expected_tables:
                if table in table_names:
                    print(f"  ✓ Table '{table}': Exists")
                else:
                    print(f"  ✗ Table '{table}': MISSING")
                    all_passed = False
            
            await conn.close()
            return True
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        return False

tables_ok = asyncio.run(check_tables())

# ============================================================================
# Final Result
# ============================================================================
print("\n" + "=" * 60)
if all_passed and tables_ok:
    print("✅ ALL CHECKS PASSED - SYSTEM READY!")
else:
    print("❌ SOME CHECKS FAILED - REVIEW CONFIGURATION")
    sys.exit(1)
print("=" * 60)
