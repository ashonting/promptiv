# backend/main.py

import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from backend.auth import get_current_user, get_optional_user
from backend.services.user_service import get_user_quota_info, get_or_create_user_by_device
from backend.routers import rewrite, paddle, webhook

# ─── Logging ────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("promptiv.main")

app = FastAPI(
    title="Promptiv API",
    description="API for Promptiv prompt rewriting service.",
    version="1.0.0",
)

# ─── CORS ───────────────────────────────────────────────────────────
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "https://promptiv.io",
    "http://localhost",
    "http://localhost:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serve static assets (favicon, style, etc) ─────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ─── Serve dashboard build & assets ────────────────────────────────
dashboard_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dashboard", "dist")
if os.path.isdir(dashboard_dist):
    assets_dir = os.path.join(dashboard_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard_assets")

    @app.get("/", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    @app.get("/dashboard/{full_path:path}", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_dashboard(full_path: str = ""):
        # Serve SPA for any unknown route except API/static/assets
        index_file = os.path.join(dashboard_dist, "index.html")
        if not os.path.exists(index_file):
            logger.error(f"Dashboard index.html not found at {index_file}")
            raise HTTPException(status_code=500, detail="Dashboard not found")
        return FileResponse(index_file)

# ─── Exception Handlers ────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(status_code=500, content={"error": "Internal server error"})

# ─── Health Check ─────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# ─── Example LLM Model List ───────────────────────────────────────
@app.get("/api/llm_count")
async def llm_count():
    return {"models": ["Claude 3 Opus", "GPT-4o", "Gemini 1.5", "Llama 3", "Mistral"]}

# ─── User/Device Endpoints ────────────────────────────────────────
@app.post("/api/user")
async def get_or_create_user(request: Request):
    data = await request.json()
    device_hash = data.get("device_hash")
    user = None
    if device_hash:
        user = get_or_create_user_by_device(device_hash)
    else:
        try:
            user = await get_current_user(request.headers.get("authorization"))
        except Exception:
            user = None
    if not user:
        raise HTTPException(status_code=401, detail="User not found or not authenticated")
    quota = get_user_quota_info(user["id"])
    return {
        "id": user["id"],
        "email": user.get("email"),
        "tier": quota.get("tier", "anonymous"),
        "quota_used": quota.get("quota_used", 0),
        "quota_limit": quota.get("quota_total", 0),
        "paddle_subscription_id": user.get("paddle_subscription_id"),
    }

@app.post("/api/user/device")
async def get_or_create_user_device(request: Request):
    return await get_or_create_user(request)

# ─── Contact Form Endpoint ────────────────────────────────────────
class ContactForm(BaseModel):
    name: str
    email: EmailStr
    message: str

@app.post("/api/contact")
async def contact(form: ContactForm):
    logger.info(f"Contact form received from {form.email}: {form.name} - {form.message[:120]}")
    # TODO: send an email or save to DB
    # For now, just acknowledge
    return {"ok": True}

# ─── Register Routers (Rewrite, Paddle, Webhook) ──────────────────
app.include_router(rewrite.router)
app.include_router(paddle.router)
app.include_router(webhook.router)
