import csv
import os
import threading
from datetime import datetime
from typing import Dict

from config import settings, logger

# ==========================================
# THREAD-SAFE STORAGE CONTROLS
# ==========================================
# Global lock to prevent file corruption during concurrent FastApi requests
_db_lock = threading.Lock()

# ==========================================
# DATABASE INITIALIZATION
# ==========================================
def initialize_database() -> None:
    """
    Creates the persistent CSV storage if it does not already exist.
    Writes the standardized header row for telemetry tracking.
    """
    file_path = settings.METRICS_FILE_PATH
    
    if not os.path.exists(file_path):
        try:
            with _db_lock:
                # Double-check inside the lock to prevent race conditions during boot
                if not os.path.exists(file_path):
                    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            "Timestamp", 
                            "Event_Type", 
                            "Semantic_Category", 
                            "Target_Asset", 
                            "Device_ID"
                        ])
            logger.info(f"[ANALYTICS] Initialized persistent storage at {file_path}")
        except Exception as e:
            logger.critical(f"[ANALYTICS] Failed to initialize database: {str(e)}")

# ==========================================
# EVENT LOGGING
# ==========================================
def log_event(event_type: str, category: str, target: str, device_id: str) -> None:
    """
    Appends a new telemetry event to the CSV log.
    Executed as a FastAPI Background Task so it doesn't block the API response.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _db_lock:
            with open(settings.METRICS_FILE_PATH, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, event_type, category, target, device_id])
    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to log event '{event_type}': {str(e)}")

# ==========================================
# DASHBOARD AGGREGATION
# ==========================================
def get_all_time_metrics() -> Dict[str, int]:
    """
    Reads the full CSV to compute high-level performance metrics.
    Returns total impressions, clicks, and unique user counts for the ops dashboard.
    """
    metrics = {"impressions": 0, "clicks": 0, "unique_users": 0}
    file_path = settings.METRICS_FILE_PATH
    
    if not os.path.exists(file_path):
        return metrics

    unique_devices = set()

    try:
        with _db_lock:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    event_type = row.get("Event_Type")
                    device_id = row.get("Device_ID")

                    # Tally primary KPIs
                    if event_type == "IMPRESSION":
                        metrics["impressions"] += 1
                    elif event_type == "CLICK":
                        metrics["clicks"] += 1
                        
                    # Track unique users based on anonymized UUID
                    if device_id:
                        unique_devices.add(device_id)

        metrics["unique_users"] = len(unique_devices)
        return metrics
        
    except Exception as e:
        logger.error(f"[ANALYTICS] Failed to aggregate metrics: {str(e)}")
        # Return whatever baseline metrics we have if the file read fails
        return metrics