import logging
import sys
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

# ==========================================
# ENVIRONMENT VALIDATION
# ==========================================
class Settings(BaseSettings):
    """
    Strict environment variable validation.
    The application will fail to boot if these are missing, preventing runtime crashes.
    """
    # Application Security
    ETHIC_API_KEY: str = "ethic_demo_key_2026"
    DEBUG: bool = False

    # External APIs (Required in .env)
    GROQ_API_KEY: str
    RAPIDAPI_KEY: str
    
    # RapidAPI Configuration (Amazon Data API)
    RAPIDAPI_HOST: str = "real-time-amazon-data.p.rapidapi.com"

    # CSV Storage Path (The sole persistence layer)
    METRICS_FILE_PATH: str = "advertiser_metrics.csv"

    # Pydantic configuration to read from .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Caches the settings so the .env file is only read and validated once on boot.
    """
    return Settings()

# ==========================================
# PRODUCTION LOGGING CONFIGURATION
# ==========================================
def setup_logger(name: str) -> logging.Logger:
    """
    Standardized enterprise logging format.
    Ensures all modules log with exact timestamps and severity levels for easier debugging.
    """
    logger = logging.getLogger(name)
    
    # Prevent adding multiple handlers if the logger is instantiated more than once
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s", 
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# ==========================================
# GLOBAL INSTANCES
# ==========================================
# These are instantiated here so other modules can import them directly
# Example: `from config import settings, logger`
logger = setup_logger("EthicAds")
settings = get_settings()