# backend/services/user_service.py

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from postgrest.exceptions import APIError
import logging

# --- Logging ---
logger = logging.getLogger("promptiv.user_service")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Env ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- Quota ---
TIER_QUOTAS = {
    "anonymous": 1,
    "basic": 3,
    "premium": 30,
    "pro": 100,
}

def create_or_update_profile(user_id, email=None, device_hash=None):
    """
    Ensure a profile exists for a user. For device/anon, synthesize a non-null email.
    """
    if not user_id:
        logger.error("create_or_update_profile called without user_id")
        return
    try:
        res = supabase.table("profiles").select("id").eq("id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return  # Profile exists

        # Generate dummy email if missing
        if not email:
            suffix = (device_hash or user_id or "unknown")
            email = f"{suffix}@anon.promptiv.io"

        profile_fields = {
            "id": user_id,
            "email": email,
            "created_at": datetime.utcnow().isoformat()
            # Add more fields as needed by your schema
        }
        supabase.table("profiles").insert(profile_fields).execute()
        logger.info(f"Inserted profile for user_id={user_id} ({email})")
    except APIError as e:
        logger.error(f"Supabase error in create_or_update_profile: {str(e)}")
        raise

def get_or_create_user_by_device(device_hash: str):
    """
    Lookup or create a device-based anonymous user in 'users' and 'profiles' tables.
    """
    try:
        # Lookup by device_hash (unique index)
        result = supabase.table("users").select("*").eq("device_hash", device_hash).limit(1).execute()
        if result.data and len(result.data) > 0:
            user = result.data[0]
            create_or_update_profile(user.get("id"), device_hash=device_hash)
            return user

        # Insert new user
        new_user = {
            "device_hash": device_hash,
            "tier": "anonymous",
            "quota_used": 0,
        }
        response = supabase.table("users").insert(new_user).execute()
        user = response.data[0]
        create_or_update_profile(user.get("id"), device_hash=device_hash)
        return user

    except APIError as e:
        logger.error(f"Supabase error in get_or_create_user_by_device: {str(e)}")
        raise ValueError(f"Supabase error in get_or_create_user_by_device: {str(e)}")

def ensure_user_exists_by_id(user_id: str, email: str = None):
    """
    Ensure a Supabase-auth user exists in both 'users' and 'profiles'.
    """
    try:
        result = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
        if not result.data or len(result.data) == 0:
            # Create user as basic tier by default
            new_user = {
                "id": user_id,
                "tier": "basic",
                "quota_used": 0
            }
            supabase.table("users").insert(new_user).execute()
        create_or_update_profile(user_id, email=email)
    except APIError as e:
        logger.error(f"Supabase error in ensure_user_exists_by_id: {str(e)}")
        raise ValueError(f"Supabase error in ensure_user_exists_by_id: {str(e)}")

def get_user_quota_info(user_id: str):
    """
    Return user's quota info (tier, used, total).
    """
    try:
        result = supabase.table("users").select("tier, quota_used").eq("id", user_id).limit(1).execute()
        if not result.data or len(result.data) == 0:
            raise ValueError(f"User with id {user_id} not found")
        user = result.data[0]
        tier = user.get("tier", "anonymous")
        used = user.get("quota_used", 0)
        total = TIER_QUOTAS.get(tier, 1)
        return {
            "tier": tier,
            "quota_used": used,
            "quota_total": total
        }
    except APIError as e:
        logger.error(f"Supabase error in get_user_quota_info: {str(e)}")
        raise ValueError(f"Supabase error in get_user_quota_info: {str(e)}")

def increment_quota(user_id: str, increment: int = 1):
    """
    Increment quota_used for user.
    """
    try:
        result = supabase.table("users").select("quota_used").eq("id", user_id).limit(1).execute()
        if not result.data or len(result.data) == 0:
            raise ValueError(f"User with id {user_id} not found for quota increment")
        current = result.data[0].get("quota_used", 0)
        new_value = current + increment
        supabase.table("users").update({"quota_used": new_value}).eq("id", user_id).execute()
    except APIError as e:
        logger.error(f"Supabase error in increment_quota: {str(e)}")
        raise ValueError(f"Supabase error in increment_quota: {str(e)}")

def get_user_by_id(user_id: str):
    """
    Get user record by ID.
    """
    try:
        result = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
        if not result.data or len(result.data) == 0:
            return None
        return result.data[0]
    except APIError as e:
        logger.error(f"Supabase error in get_user_by_id: {str(e)}")
        raise ValueError(f"Supabase error in get_user_by_id: {str(e)}")
