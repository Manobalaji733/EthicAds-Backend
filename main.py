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

# CORS Configuration
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

class TelemetryPayload(BaseModel):
    event_type: str
    category: str
    target: str
    device_id: str

# ==========================================
# ROUTES
# ==========================================
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard")
async def serve_ops_dashboard():
    return FileResponse("static/dashboard.html")

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

@app.post("/analytics/log")
async def log_telemetry_event(
    payload: TelemetryPayload, 
    background_tasks: BackgroundTasks
):
    """Receives telemetry from the Chrome Extension and logs it to Google Sheets."""
    background_tasks.add_task(
        analytics.log_event, 
        payload.event_type, 
        payload.category, 
        payload.target, 
        payload.device_id
    )
    background_tasks.add_task(
        stream.broadcast, 
        "TELEMETRY_LOGGED", 
        {"type": payload.event_type, "category": payload.category}
    )
    return {"status": "success", "message": "Event logged"}

@app.post("/api/v1/workflows/run")
@security.limiter.limit("60/minute")
async def runtime_pipeline(
    request: Request,
    payload: ContextPayload, 
    background_tasks: BackgroundTasks
    # api_key: str = Depends(security.get_api_key) # <-- COMMENTED OUT FOR EMERGENCY OVERRIDE
):
    extracted_intent = await svc.extract_semantic_intent(payload.raw_viewport_text)
    if not extracted_intent or extracted_intent == "general": 
        return {"status": "success", "ads": []}

    target_ads = await svc.fetch_amazon_inventory(extracted_intent)
    
    if target_ads:
        background_tasks.add_task(stream.broadcast, "INVENTORY_MATCH", {"intent": extracted_intent, "count": len(target_ads)})
        background_tasks.add_task(analytics.log_event, "IMPRESSION", extracted_intent, f"{len(target_ads)} items served", payload.device_id)

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