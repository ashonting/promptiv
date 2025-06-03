import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.services.rewrite_service import rewrite_prompt
from backend.services.openai_utils import LLM_MAP

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files ---
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# --- Root homepage ---
@app.get("/", response_class=HTMLResponse)
def serve_index():
    return Path("frontend/index.html").read_text()

# --- Legal/Policy/Extensionless pages ---
@app.get("/pricing", response_class=HTMLResponse)
def serve_pricing():
    return Path("frontend/pricing.html").read_text()

@app.get("/terms", response_class=HTMLResponse)
def serve_terms():
    return Path("frontend/terms.html").read_text()

@app.get("/privacy", response_class=HTMLResponse)
def serve_privacy():
    return Path("frontend/privacy.html").read_text()

@app.get("/refund-policy", response_class=HTMLResponse)
def serve_refund_policy():
    return Path("frontend/refund-policy.html").read_text()

# --- API endpoints ---
from fastapi import Request, HTTPException

@app.post("/api/rewrite")
async def rewrite_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse JSON: {e}")

    prompt_text = body.get("prompt")
    if not prompt_text or not isinstance(prompt_text, str):
        raise HTTPException(status_code=422, detail="Field 'prompt' is required and must be a string.")

    # Capture user metadata
    user = {
        "id": "00000000-0000-0000-0000-000000000000",      # Replace with real user ID logic if available
        "tier": "premium",                                 # Replace with real plan if available
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None
    }

    try:
        result = rewrite_prompt({"prompt": prompt_text}, user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {str(e)}")


@app.get("/api/llm_count")
def get_llm_count():
    models = sorted(set(LLM_MAP.values()))
    return {
        "count": len(models),
        "models": models
    }
