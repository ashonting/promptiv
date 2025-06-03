# backend/routers/rewrite.py

from fastapi import APIRouter, HTTPException, Request
from backend.services.rewrite_service import rewrite_prompt
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/rewrite")
async def rewrite(request: Request):
    """
    Accept a prompt as JSON and return rewritten variants.
    """
    try:
        body = await request.json()
        prompt_text = body.get("prompt", "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse JSON: {e}")

    if not prompt_text or not isinstance(prompt_text, str):
        raise HTTPException(status_code=422, detail="Field 'prompt' is required and must be a string.")

    user = {"username": body.get("username", "test")}
    try:
        logger.info(f"[Promptiv] User {user['username']} submitted prompt: {prompt_text}")
        result = rewrite_prompt({"prompt": prompt_text}, user)
        return result
    except ValueError as ve:
        logger.warning(f"[Promptiv] Value error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"[Promptiv] Server error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Server error. Please try again.")
