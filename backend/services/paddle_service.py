# backend/services/paddle_service.py

import os
import logging
import httpx
from dotenv import load_dotenv

# --- Logger Setup ---
logger = logging.getLogger("promptiv.paddle")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Load Environment ---
load_dotenv()
PADDLE_VENDOR_ID = os.getenv("PADDLE_VENDOR_ID")
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY") or os.getenv("PADDLE_VENDOR_AUTH_CODE")
PADDLE_API_URL = "https://vendors.paddle.com/api/2.0/subscription/users_manage"
PADDLE_CHECKOUT_PRODUCT_ID = os.getenv("PADDLE_PRODUCT_ID", "YOUR_PRODUCT_ID")  # <-- set this in your .env!

def generate_checkout_link(email: str) -> str:
    """
    Returns a Paddle Checkout link for your product, optionally with email prefilled.
    You may want to use Paddle's advanced API for custom sessions, but this suffices for standard use.
    """
    if not PADDLE_CHECKOUT_PRODUCT_ID:
        logger.error("Paddle Product ID missing. Set PADDLE_PRODUCT_ID in your .env.")
        raise RuntimeError("Paddle Product ID not set.")
    # Prefill email for Paddle, optional but nice UX
    return f"https://pay.paddle.com/checkout/{PADDLE_CHECKOUT_PRODUCT_ID}?email={email}"

def generate_manage_link(subscription_id: str) -> str:
    """
    Generates a Paddle customer portal link for managing a subscription.
    """
    if not PADDLE_VENDOR_ID or not PADDLE_API_KEY:
        logger.error("Missing Paddle credentials in environment.")
        raise RuntimeError("Paddle credentials are not set in environment variables.")

    if not subscription_id:
        logger.error("Subscription ID is required but not provided.")
        raise ValueError("Subscription ID is required.")

    payload = {
        "vendor_id": PADDLE_VENDOR_ID,
        "vendor_auth_code": PADDLE_API_KEY,
        "subscription_id": subscription_id,
    }

    try:
        with httpx.Client(timeout=12) as client:
            response = client.post(PADDLE_API_URL, data=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                return data["response"]["url"]
            else:
                error_info = data.get("error", data)
                logger.error("Paddle API responded with error: %s", error_info)
                raise RuntimeError(f"Paddle API error: {error_info}")

    except httpx.HTTPError as e:
        logger.exception("HTTP error during Paddle API request")
        raise RuntimeError(f"HTTP request to Paddle failed: {e}")
    except Exception as e:
        logger.exception("Unexpected error during Paddle API call")
        raise
