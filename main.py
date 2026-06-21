import os
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import logger, settings
import security
import services as svc
import analytics
from telemetry import stream

# ==========================================
# APP INITIALIZATION & MIDDLEWARE
# ==========================================
app = FastAPI(title="EthicAds Engine", version="6.0.0")

# Rate Limiting Configuration
app.state.limiter = security.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==========================================
# CORS CONFIGURATION (The Fix)
# ==========================================
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Static file mounting
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info("[MAIN] Booting EthicAds privacy-first ad server...")
    analytics.initialize_database()

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class ContextPayload(BaseModel):
    raw_viewport_text: str = Field(..., min_length=10, max_length=5000)
    device_id: str = Field(..., min_length=5, max_length=50)

# ==========================================
# DASHBOARD & METRICS ROUTES
# ==========================================
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard")
async def serve_ops_dashboard():
    dashboard_path = "static/dashboard.html"
    if not os.path.exists(dashboard_path):
        return {"error": "Dashboard UI not found in the static/ folder. Please place dashboard.html there."}
    return FileResponse(dashboard_path)

@app.get("/api/v1/metrics/totals")
async def get_historical_metrics():
    return analytics.get_all_time_metrics()

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await stream.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        stream.disconnect(websocket)

# ==========================================
# CORE ADVERTISING WORKFLOWS
# ==========================================
@app.post("/api/v1/workflows/run")
@security.limiter.limit("60/minute")
async def runtime_pipeline(
    request: Request,
    payload: ContextPayload, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(security.get_api_key) # Using the correct function name here
):
    logger.info(f"[MAIN] Processing pipeline for device {payload.device_id[:8]}...")
    
    # 1. AI Intent Extraction
    extracted_intent = await svc.extract_semantic_intent(payload.raw_viewport_text)
    if not extracted_intent or extracted_intent == "general": 
        return {"status": "success", "ads": []}

    # 2. Amazon Product Retrieval
    target_ads = await svc.fetch_amazon_inventory(extracted_intent)
    
    # 3. Asynchronous Telemetry & Logging
    if target_ads:
        background_tasks.add_task(
            stream.broadcast, 
            "INVENTORY_MATCH", 
            {"intent": extracted_intent, "count": len(target_ads)}
        )
        background_tasks.add_task(
            analytics.log_event, 
            "IMPRESSION", 
            extracted_intent, 
            f"{len(target_ads)} items served", 
            payload.device_id
        )

    return {"status": "success", "ads": target_ads}

@app.get("/api/v1/clicks")
@security.limiter.limit("120/minute")
async def direct_conversion_proxy(
    request: Request,
    ad_id: str, 
    dest: str, 
    device_id: str, 
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(stream.broadcast, "CLICK_CONVERSION", {"ad_id": ad_id})
    background_tasks.add_task(analytics.log_event, "CLICK", "User_Interaction", ad_id, device_id)
    return RedirectResponse(url=dest)