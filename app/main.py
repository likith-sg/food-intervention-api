"""
main.py — Real-Time Food Intervention System v3 (AI-powered)
"""
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from app.agents.scoring_agent import compute_score
from app.agents.context_agent import get_intervention, get_decision
from app.agents.behavior_agent import detect_pattern
from app.agents.ai_agent import generate_ai_analysis

# ── Firebase ───────────────────────────────────────────────────────────────────
firebase_available = False
db = None
try:
    import base64, firebase_admin
    from firebase_admin import credentials, firestore
    b64 = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if b64:
        cred = credentials.Certificate(json.loads(base64.b64decode(b64).decode()))
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        firebase_available = True
    elif path and Path(path).exists():
        firebase_admin.initialize_app(credentials.Certificate(path))
        db = firestore.client()
        firebase_available = True
except Exception:
    pass

# ── Local fallback ─────────────────────────────────────────────────────────────
HISTORY_PATH = Path("data/user_history.json")
HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
if not HISTORY_PATH.exists():
    HISTORY_PATH.write_text("[]")
MAX_HISTORY = 10

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Food Intervention API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["Content-Type"])
app.mount("/css", StaticFiles(directory="css"), name="css")
if Path("assets").exists():
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# ── Models ─────────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    food: str
    time: str
    mood: Optional[str] = None

    @field_validator("food")
    @classmethod
    def sanitize_food(cls, v):
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("food must be 1-100 characters")
        if not re.match(r"^[a-zA-Z0-9 '\-]+$", v):
            raise ValueError("food contains invalid characters")
        return v.lower()

    @field_validator("time")
    @classmethod
    def validate_time(cls, v):
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("time must be HH:MM")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("time out of range")
        return v

    @field_validator("mood")
    @classmethod
    def sanitize_mood(cls, v):
        if v is None:
            return None
        v = v.strip()
        if len(v) > 50:
            raise ValueError("mood too long")
        if not re.match(r"^[a-zA-Z ]+$", v):
            raise ValueError("mood contains invalid characters")
        return v.lower()

# ── Storage ────────────────────────────────────────────────────────────────────
def load_local():
    try:
        return json.loads(HISTORY_PATH.read_text())
    except Exception:
        return []

def save_local(history):
    try:
        HISTORY_PATH.write_text(json.dumps(history[-MAX_HISTORY:], indent=2))
    except Exception:
        pass

def load_history():
    if firebase_available and db:
        try:
            docs = db.collection("food_entries").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(MAX_HISTORY).stream()
            return [d.to_dict() for d in docs]
        except Exception:
            pass
    return load_local()

def save_entry(entry):
    if firebase_available and db:
        try:
            db.collection("food_entries").add(entry)
            return
        except Exception:
            pass
    h = load_local()
    h.append(entry)
    save_local(h)

# ── Exception handlers ─────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})

@app.exception_handler(422)
async def validation_error(request: Request, exc):
    return JSONResponse(status_code=422, content={"error": "Validation failed", "detail": str(exc)})

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def serve_ui():
    return FileResponse("index.html")

@app.get("/auth")
def serve_auth():
    return FileResponse("auth.html")

@app.get("/app")
def serve_app():
    return FileResponse("app.html")

@app.get("/health")
def health():
    ai_available = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    return {"status": "ok", "firebase": firebase_available, "ai_powered": ai_available, "version": "3.0.0"}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    history = load_history()
    scoring = compute_score(req.food, req.time, history)
    score = scoring["score"]
    food_class = scoring["food_class"]
    deductions = scoring["deductions"]
    confidence = scoring["confidence"]

    intervention_level = get_intervention(score)
    decision = get_decision(intervention_level)
    pattern = detect_pattern(history, req.time)

    # AI-powered analysis (falls back to deterministic if API key absent)
    ai = generate_ai_analysis(
        food=req.food,
        food_class=food_class,
        score=score,
        time_str=req.time,
        mood=req.mood,
        pattern=pattern,
        recent_history=history,
        deductions=deductions,
        confidence=confidence,
    )

    save_entry({
        "food": req.food,
        "time": req.time,
        "decision": decision,
        "health_score": score,
        "intervention_level": intervention_level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "health_score": score,
        "decision": decision,
        "intervention_level": intervention_level,
        "intervention_message": ai["intervention_message"],
        "reasoning": ai["reasoning"],
        "pattern_detected": pattern,
        "future_risk": ai["future_risk"],
        "better_alternatives": ai["better_alternatives"],
        "confidence": confidence,
    }
