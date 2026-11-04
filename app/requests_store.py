import json
import random
import string
from datetime import datetime
from typing import List, Dict, Any
from app.config import REQUESTS_FILE

def generate_request_id() -> str:
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"SOL-{suffix}"

def load_all_requests() -> List[Dict[str, Any]]:
    if not REQUESTS_FILE.exists():
        return []
    try:
        with open(REQUESTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_travel_request(session_id: str, data: Dict[str, Any]) -> str:
    requests = load_all_requests()
    
    req_id = generate_request_id()
    record = {
        "request_id": req_id,
        "session_id": session_id,
        "service_type": data.get("service_type", "Viaje corporativo"),
        "destination": data.get("destination", "No especificado"),
        "travel_date": data.get("travel_date", "No especificado"),
        "passengers": int(data.get("passengers", 1)),
        "customer_name": data.get("customer_name", "Cliente"),
        "customer_phone": data.get("customer_phone", "No especificado"),
        "customer_email": data.get("customer_email", "correo@ejemplo.com"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    requests.append(record)
    
    REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REQUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, indent=2, ensure_ascii=False)
        
    return req_id
