from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import json
import os

# Import local modules from your project structure
from config import settings
from security import verify_api_key
from services import ad_engine
from telemetry import telemetry_manager
from analytics import analytics_store

app = FastAPI(
    title="EthicAds - Privacy-First Contextual Advertising Engine",
    version="1.0.0"
)

# ==========================================
# CORS MIDDLEWARE CONFIGURATION
# ==========================================
# This allows your Chrome Extension running on external web pages 
# to securely make requests to your Render backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# ==========================================
# PUNDANTIC SCHEMAS
# ==========================================
class ContextPayload(BaseModel):
    raw_viewport_text: str
    device_id: str

# ==========================================
# ROUTES & ENDPOINTS
# ==========================================

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root traffic to the telemetry dashboard."""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the central telemetry monitoring interface."""
    dashboard_path = os.path.join("static", "dashboard.html")
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=404, detail="Dashboard HTML file not found.")
    
    with open(dashboard_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/v1/workflows/run")
async def run_contextual_pipeline(
    payload: ContextPayload, 
    authenticated: bool = Depends(verify_api_key)
):
    """
    Analyzes page text, matches privacy-safe inventory, logs 
    the impression, and broadcasts telemetry updates to the dashboard.
    """
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API Key"
        )
    
    # Process text through the NLP/Matching logic
    result = await ad_engine.match_inventory(payload.raw_viewport_text, payload.device_id)
    
    if result["status"] == "success" and result["ads"]:
        # Log historical metrics locally
        analytics_store.log_impression(len(result["ads"]), payload.device_id)
        
        # Broadcast real-time update to the dashboard over WebSockets
        await telemetry_manager.broadcast({
            "type": "INVENTORY_MATCH",
            "data": {
                "intent": result.get("detected_intent", "Unknown"),
                "count": len(result["ads"])
            }
        })
        
    return result


@app.get("/api/v1/clicks")
async def handle_click_tracking(ad_id: str, dest: str, device_id: str):
    """Tracks ad clicks without cookies and routes the user to their destination."""
    # Log click metrics locally
    analytics_store.log_click(ad_id, device_id)
    
    # Broadcast click event to open WebSocket connections
    await telemetry_manager.broadcast({
        "type": "CLICK_CONVERSION",
        "data": {
            "ad_id": ad_id
        }
    })
    
    # Securely redirect user to the target landing page
    return RedirectResponse(url=dest)


@app.get("/api/v1/metrics/totals")
async def get_historical_metrics():
    """Retrieve cumulative performance data for the KPI layout."""
    return analytics_store.get_summary_stats()

# ==========================================
# WEBSOCKET CHANNELS
# ==========================================

@app.websocket("/ws/telemetry")
async def telemetry_websocket_endpoint(websocket: WebSocket):
    """Handles persistent live connections from monitoring interfaces."""
    await telemetry_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; look out for incoming client heartbeats
            await websocket.receive_text()
    except WebSocketDisconnect:
        telemetry_manager.disconnect(websocket)