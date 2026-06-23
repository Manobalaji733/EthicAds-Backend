import json
import hashlib
import time
import threading
import httpx
from typing import List, Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings, logger
from security import sanitize_text

# ==========================================
# SEMANTIC CACHE LAYER
# ==========================================
class CacheEntry:
    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expiry = time.time() + ttl

class SemanticCache:
    """Thread-safe, in-memory cache using SHA-256 to prevent duplicate external API calls."""
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get(self, text: str) -> Optional[Any]:
        key = self._hash(text)
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                if time.time() < entry.expiry:
                    return entry.data
                else:
                    del self._cache[key]
        return None

    def set(self, text: str, data: Any, ttl: int = 3600) -> None:
        key = self._hash(text)
        with self._lock:
            self._cache[key] = CacheEntry(data, ttl)
            
    def cleanup(self) -> None:
        """Removes expired entries from the cache."""
        now = time.time()
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if now >= v.expiry]
            for k in expired_keys:
                del self._cache[k]

_CACHE = SemanticCache()

# ==========================================
# GROQ INTELLIGENCE ENGINE
# ==========================================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)
async def _call_groq_api(clean_text: str) -> Dict[str, Any]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        # Using Llama 3.1 8B for highly optimized, low-latency JSON structured outputs
        "model": "llama-3.1-8b-instant", 
        "messages": [
            {
                "role": "system", 
                "content": "You are a contextual advertising classifier. You must respond strictly in JSON format."
            },
            {
                "role": "user", 
                "content": (
                    "Analyze the following webpage text. Determine the single best, broad e-commerce product "
                    "category for contextual advertising (e.g., 'laptops', 'cameras', 'mens shoes', 'skincare'). "
                    "Keep it to 1 or 2 words maximum. Do not be overly specific.\n"
                    "Output strictly as json: {\"broad_category\": \"str\"}\n\n"
                    f"Text: {clean_text}"
                )
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
        "max_tokens": 150
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=8.0)
        
        if resp.status_code != 200:
            logger.error(f"[SERVICES] Groq API rejected request. Reason: {resp.text}")
            
        resp.raise_for_status()
        return resp.json()

async def extract_semantic_intent(raw_text: str) -> str:
    """Extracts a broad category using Groq with strict JSON output recovery."""
    clean_text = sanitize_text(raw_text)
    if not clean_text:
        logger.warning("[SERVICES] Empty text provided after sanitization.")
        return ""

    cache_prefix = f"groq_{clean_text}"
    cached_intent = _CACHE.get(cache_prefix)
    if cached_intent:
        logger.info("[SERVICES] Cache hit for semantic intent.")
        return cached_intent

    try:
        data = await _call_groq_api(clean_text)
        content = data["choices"][0]["message"]["content"]
        
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("[SERVICES] Malformed JSON from Groq. Attempting recovery.")
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                parsed = json.loads(content[start:end+1])
            else:
                raise ValueError("Valid JSON structure not found in Groq response.")

        # Extract the broad category, fallback to 'general' if missing
        search_query = parsed.get("broad_category", "").strip().lower()
        if not search_query:
            search_query = "general"
            
        _CACHE.set(cache_prefix, search_query, ttl=3600)
        logger.info(f"[SERVICES] Extracted broad intent query: '{search_query}'")
        return search_query

    except Exception as e:
        logger.error(f"[SERVICES] Groq NLP extraction failed: {str(e)}")
        return "general"

# ==========================================
# AMAZON RAPIDAPI ENGINE
# ==========================================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=2, max=12),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)
async def _call_rapidapi(intent: str) -> Dict[str, Any]:
    url = f"https://{settings.RAPIDAPI_HOST}/search"
    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": settings.RAPIDAPI_HOST
    }
    # Append 'eco friendly' to ensure sustainable ads are returned
    params = {
        "query": f"eco friendly {intent}",
        "country": "US",
        "category_id": "aps"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params, timeout=12.0)
        if resp.status_code == 429:
            logger.warning("[SERVICES] RapidAPI rate limit exceeded. Tenacity will retry.")
        resp.raise_for_status()
        return resp.json()

async def fetch_amazon_inventory(intent: str) -> List[Dict[str, str]]:
    """Fetches, ranks, and normalizes real Amazon products via RapidAPI."""
    if not intent or intent == "general":
        return []

    cache_prefix = f"amazon_{intent}"
    cached_inventory = _CACHE.get(cache_prefix)
    if cached_inventory:
        logger.info(f"[SERVICES] Cache hit for Amazon inventory matching: '{intent}'")
        return cached_inventory

    try:
        data = await _call_rapidapi(intent)
        products = data.get("data", {}).get("products", [])
        
        normalized_products = []
        for p in products[:3]:
            if not p.get("asin"): 
                continue
            # FIXED: 'id' and 'url' keys now exactly match what the extension frontend expects
            normalized_products.append({
                "id": p.get("asin"),
                "title": p.get("product_title", "Amazon Product"),
                "price": p.get("product_price", "Check Price"),
                "url": p.get("product_url", "#"),
                "image": p.get("product_photo", "")
            })

        _CACHE.set(cache_prefix, normalized_products, ttl=1800)
        logger.info(f"[SERVICES] Successfully retrieved {len(normalized_products)} products for '{intent}'")
        return normalized_products

    except Exception as e:
        logger.error(f"[SERVICES] Amazon Product API failed: {str(e)}")
        return []