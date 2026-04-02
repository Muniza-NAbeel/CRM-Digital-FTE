#!/usr/bin/env python
"""Simple .env test"""
import os

# Method 1: Direct file reading
print("=== Method 1: Direct file reading ===")
with open('.env', 'r', encoding='utf-8') as f:
    for line in f:
        if 'TWILIO' in line or 'GMAIL' in line:
            print(f"  {line.strip()}")

# Method 2: python-dotenv
print("\n=== Method 2: python-dotenv ===")
from dotenv import dotenv_values
values = dotenv_values('.env')
print(f"  APP_TWILIO_ACCOUNT_SID: {values.get('APP_TWILIO_ACCOUNT_SID')}")
print(f"  APP_GMAIL_CLIENT_ID: {values.get('APP_GMAIL_CLIENT_ID')}")

# Method 3: load_dotenv + os.environ
print("\n=== Method 3: load_dotenv + os.environ ===")
from dotenv import load_dotenv
load_dotenv('.env', override=True)
print(f"  APP_TWILIO_ACCOUNT_SID: {os.environ.get('APP_TWILIO_ACCOUNT_SID')}")
print(f"  APP_GMAIL_CLIENT_ID: {os.environ.get('APP_GMAIL_CLIENT_ID')}")

# Method 4: pydantic-settings
print("\n=== Method 4: pydantic-settings ===")
from pydantic_settings import BaseSettings, SettingsConfigDict

class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='APP_',
        env_file='.env',
        env_file_encoding='utf-8',
    )
    twilio_account_sid: str = ''
    gmail_client_id: str = ''

settings = TestSettings()
print(f"  twilio_account_sid: {settings.twilio_account_sid}")
print(f"  gmail_client_id: {settings.gmail_client_id}")
