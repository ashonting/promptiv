# backend/auth.py

import os
import logging
import requests
from fastapi import Depends, HTTPException, Header, status
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger("promptiv.auth")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Load environment
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY")

def get_current_user(authorization: str = Header(...)):
    """
    REQUIRED auth. Used for dashboard, pro features, etc.
    """
    if not authorization.startswith("Bearer "):
        logger.warning("Malformed Authorization header")
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = authorization.split("Bearer ")[1].strip()
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": SUPABASE_ANON_KEY
        }
        resp = requests.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers)
        if resp.status_code != 200:
            logger.warning(f"Supabase token rejected: {resp.status_code} - {resp.text}")
            raise HTTPException(status_code=401, detail="Invalid Supabase token")

        user = resp.json()
        logger.info(f"Authenticated user {user.get('id')} ({user.get('email')})")
        return user

    except Exception as e:
        logger.exception("Error validating Supabase token")
        raise HTTPException(status_code=500, detail="Token validation failed")

def get_optional_user(authorization: str = Header(None)):
    """
    OPTIONAL auth. Returns user if present/valid, else None.
    Used for endpoints that support anonymous + authenticated users.
    """
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException as e:
        if e.status_code == 401:
            return None
        raise
