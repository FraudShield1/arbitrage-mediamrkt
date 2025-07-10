"""
Application configuration using Pydantic BaseSettings.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, AnyUrl, BaseSettings, Field
from functools import lru_cache

class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @property
    def environment(self) -> str:
        """Lowercase environment for compatibility."""
        return self.ENVIRONMENT.lower()
    
    @property
    def app_version(self) -> str:
        """Application version."""
        return "1.0.0"

    # MongoDB Settings
    MONGODB_URL: str
    DATABASE_URL: Optional[str] = None  # Will use MONGODB_URL if not set
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cross-Market Arbitrage Tool"
    
    # Telegram Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Dashboard Configuration
    DASHBOARD_PORT: int = 8501
    STREAMLIT_SERVER_PORT: int = 8501
    STREAMLIT_SERVER_ADDRESS: str = "0.0.0.0"

    # Monitoring
    FLOWER_PORT: int = 5555

    # External API Keys
    KEEPA_API_KEY: Optional[str] = None
    AMAZON_ACCESS_KEY: Optional[str] = None
    AMAZON_SECRET_KEY: Optional[str] = None
    AMAZON_ASSOCIATE_TAG: Optional[str] = None

    # Notification Configuration
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = None  # Secret token for webhook verification
    TELEGRAM_WEBHOOK_URL: Optional[str] = None  # Full URL for Telegram webhook endpoint
    SLACK_WEBHOOK_URL: Optional[AnyUrl] = None
    SLACK_CHANNEL: str = "#arbitrage-alerts"

    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "Arbitrage Tool"

    # Scraping Configuration
    SCRAPING_DELAY_MIN: float = 1.0
    SCRAPING_DELAY_MAX: float = 3.0
    SCRAPING_CONCURRENT_LIMIT: int = 5
    SCRAPING_RETRY_ATTEMPTS: int = 3
    SCRAPING_TIMEOUT: int = 30

    # Security Configuration
    API_RATE_LIMIT: int = 100
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8501", "http://0.0.0.0:8501"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "0.0.0.0"]

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: Optional[str] = None  # Disable file logging for local dev

    # Analysis Configuration
    MIN_PROFIT_MARGIN: float = 0.30
    MIN_PROFIT_AMOUNT: float = 10.00
    PRICE_HISTORY_DAYS: int = 90
    ALERT_COOLDOWN_HOURS: int = 24

    # Matching Configuration
    EAN_MATCH_CONFIDENCE: float = 0.95
    FUZZY_MATCH_CONFIDENCE: float = 0.85
    SEMANTIC_MATCH_CONFIDENCE: float = 0.80

    # Performance Configuration
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    CELERY_WORKER_CONCURRENCY: int = 4

    @field_validator('SLACK_WEBHOOK_URL', mode='before')
    @classmethod
    def validate_optional_urls(cls, v):
        """Convert empty strings to None for optional URL fields."""
        if v == '' or v is None:
            return None
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use MONGODB_URL as DATABASE_URL if not set
        if not self.DATABASE_URL and self.MONGODB_URL:
            self.DATABASE_URL = self.MONGODB_URL

@lru_cache()
def get_settings() -> Settings:
    _settings = Settings()
    return _settings

settings = get_settings() 