# backend/routers/webhook.py

from fastapi import APIRouter, Request, HTTPException
from starlette.responses import JSONResponse
import os
import logging
from supabase import create_client
from dotenv import load_dotenv

router = APIRouter()

# --- Logger Setup ---
logger = logging.getLogger("promptiv.webhook")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Supabase client setup ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@router.post("/api/paddle/webhook")
async def paddle_webhook(request: Request):
    """
    Paddle webhook endpoint for subscription events.
    Updates user plan status in Supabase based on Paddle events.
    """
    try:
        form = await request.form()
        event_type = form.get("alert_name")
        subscription_id = form.get("subscription_id")
        user_email = form.get("email")
        logger.info(f"[Paddle Webhook] Event: {event_type}, Sub: {subscription_id}, Email: {user_email}")

        if not user_email:
            logger.warning("No email in Paddle webhook event")
            return JSONResponse({"success": False, "error": "Missing email"})

        # Find user in Supabase by email
        user_resp = supabase.table("users").select("*").eq("email", user_email).single().execute()
        user = getattr(user_resp, "data", None)

        if not user:
            logger.warning(f"User not found in Supabase for email: {user_email}")
            return JSONResponse({"success": False, "error": "User not found"})

        update_fields = {}

        if subscription_id:
            update_fields["paddle_subscription_id"] = subscription_id

        if event_type == "subscription_payment_succeeded":
            update_fields["tier"] = "pro"
            update_fields["subscription_status"] = "active"
            logger.info(f"Upgrading user {user_email} to PRO.")

        elif event_type == "subscription_cancelled":
            update_fields["tier"] = "basic"
            update_fields["subscription_status"] = "cancelled"
            logger.info(f"Downgrading user {user_email} to BASIC.")

        elif event_type == "subscription_updated":
            # Paddle sends this on plan changes, etc.
            update_fields["subscription_status"] = "updated"
            logger.info(f"Subscription updated for user {user_email}.")

        if update_fields:
            supabase.table("users").update(update_fields).eq("email", user_email).execute()

        return JSONResponse({"success": True})

    except Exception as e:
        logger.exception("Error handling Paddle webhook event")
        raise HTTPException(status_code=500, detail=str(e))
