import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_KEY: str = os.getenv("API_KEY", "default_api_key")
    CHROME_EXTENSION_ID: str = os.getenv("CHROME_EXTENSION_ID", "default_extension_id")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # Google Fact Check API
    GOOGLE_FACT_CHECK_API_KEY: Optional[str] = os.getenv("GOOGLE_FACT_CHECK_API_KEY")
    
    # Model Configuration
    MODEL_NAME: str = os.getenv("MODEL_NAME", "distilbert-base-uncased-finetuned-fake-news")
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
    API_CACHE_TTL_HOURS: int = int(os.getenv("API_CACHE_TTL_HOURS", "1"))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = [
        f"chrome-extension://{os.getenv('CHROME_EXTENSION_ID', 'default_extension_id')}",
        "http://localhost:3000",  # For development
        "http://localhost:8000"   # For development
    ]

# Global settings instance
settings = Settings()
