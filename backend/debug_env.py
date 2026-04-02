#!/usr/bin/env python
"""Debug .env loading"""
from pathlib import Path
import os

print(f"Current working directory: {os.getcwd()}")

# Check config.py location
config_file = Path(__file__).parent / "src" / "config.py"
print(f"Config file exists: {config_file.exists()}")

# Check backend/.env
backend_env = Path(__file__).parent / ".env"
print(f"backend/.env exists: {backend_env.exists()}")
print(f"backend/.env absolute path: {backend_env.absolute()}")

# Check root/.env
root_env = Path(__file__).parent.parent / ".env"
print(f"root/.env exists: {root_env.exists()}")

# Now load settings
from src.config import settings

print("\n=== Settings Loaded ===")
print(f"Twilio Account SID: '{settings.twilio_account_sid}'")
print(f"Twilio Auth Token: '{settings.twilio_auth_token}'")
print(f"Twilio WhatsApp: '{settings.twilio_whatsapp_number}'")
print(f"Gmail Client ID: '{settings.gmail_client_id}'")
