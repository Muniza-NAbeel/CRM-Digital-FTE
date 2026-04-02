"""
Application configuration management.
Environment-based settings using pydantic-settings.
"""

import os
from functools import lru_cache
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from backend folder BEFORE anything else
# This ensures environment variables are set before pydantic reads them
ENV_FILE_PATH = Path(__file__).parent.parent / ".env"
if ENV_FILE_PATH.exists():
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True, verbose=False)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Environment variables are prefixed with APP_ to avoid conflicts.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        # Don't load .env here - we already loaded it above
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========================================================================
    # Application
    # ========================================================================
    app_name: str = "Customer Success Digital FTE"
    app_env: str = "development"  # development, staging, production
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # ========================================================================
    # Database - PostgreSQL
    # ========================================================================
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "customer_success_fte"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_ssl_mode: str = "disable"  # disable, require, verify-full
    
    # Connection pool settings
    db_min_connections: int = 5
    db_max_connections: int = 20
    db_command_timeout: int = 60
    
    # Convenience: Full database URL (alternative to individual settings)
    database_url: Optional[str] = None
    
    # Fallback database URL (for high availability)
    fallback_database_url: Optional[str] = None
    
    @property
    def db_dsn(self) -> str:
        """
        Build PostgreSQL DSN from individual settings.
        If database_url is provided, use that instead.
        """
        if self.database_url:
            return self.database_url
        
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    # ========================================================================
    # Kafka
    # ========================================================================
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_inbound: str = "inbound_messages"
    kafka_topic_outbound: str = "outbound_messages"
    kafka_topic_events: str = "agent_events"
    kafka_consumer_group_id: str = "digital_fte_worker"
    kafka_auto_offset_reset: str = "earliest"
    kafka_session_timeout_ms: int = 30000
    
    # ========================================================================
    # OpenAI
    # ========================================================================
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7
    openai_timeout_seconds: int = 30
    
    # ========================================================================
    # Channel Configs - WhatsApp (Twilio)
    # ========================================================================
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""  # Format: whatsapp:+14155238886

    # ========================================================================
    # Channel Configs - Gmail
    # ========================================================================
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = ""
    gmail_refresh_token: str = ""
    gmail_sender_email: str = ""  # Email address to send from
    gmail_polling_enabled: bool = False
    gmail_polling_interval_seconds: int = 60
    gmail_pubsub_enabled: bool = False
    
    # ========================================================================
    # Security
    # ========================================================================
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Keys (comma-separated format: "key:name:tier:limit")
    api_keys: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    @property
    def cors_origins_list(self) -> list:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # ========================================================================
    # Logging
    # ========================================================================
    log_level: str = "INFO"
    log_format: str = "json"  # json, text
    
    # ========================================================================
    # Feature Flags
    # ========================================================================
    enable_sentiment_analysis: bool = True
    enable_auto_escalation: bool = True
    enable_knowledge_base_learning: bool = True
    enable_metrics_collection: bool = True
    
    # ========================================================================
    # SLA Configuration (hours)
    # ========================================================================
    sla_first_response_standard: int = 24
    sla_first_response_premium: int = 4
    sla_first_response_enterprise: int = 1
    
    sla_resolution_standard: int = 72
    sla_resolution_premium: int = 24
    sla_resolution_enterprise: int = 8


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures settings are loaded once
    and reused throughout the application lifecycle.

    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
