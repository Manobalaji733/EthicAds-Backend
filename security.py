import hashlib
import re
from fastapi import Security, HTTPException, Request
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings, logger

# ==========================================
# API KEY VALIDATION
# ==========================================
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validates the API key from incoming extension requests.
    Raises a 403 Forbidden HTTP exception if the key is missing or invalid.
    """
    if not api_key:
        logger.warning("[SECURITY] Blocked request: Missing X-API-Key header.")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="Missing API Key"
        )
    
    if api_key != settings.ETHIC_API_KEY:
        logger.warning("[SECURITY] Blocked request: Invalid API Key attempt.")
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, 
            detail="Invalid API Key"
        )
    
    return api_key

# ==========================================
# PRIVACY-PRESERVING RATE LIMITING
# ==========================================
def privacy_aware_key_func(request: Request) -> str:
    """
    Hashes the user's IP address before passing it to the rate limiter.
    Ensures raw IP addresses are never kept in the limiter's memory space,
    aligning with the privacy-first architecture.
    """
    raw_ip = get_remote_address(request)
    return hashlib.sha256(raw_ip.encode('utf-8')).hexdigest()

limiter = Limiter(key_func=privacy_aware_key_func, default_limits=["60/minute"])

# ==========================================
# INPUT SANITIZATION
# ==========================================
def sanitize_text(text: str) -> str:
    """
    Removes HTML tags, potential scripts, and normalizes whitespace 
    before the text is sent to the LLM or external APIs.
    """
    if not text:
        return ""
        
    # Strip HTML tags
    cleaner = re.compile('<.*?>')
    text = re.sub(cleaner, '', text)
    
    # Basic whitespace normalization
    return " ".join(text.split())