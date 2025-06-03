# backend/auth.py

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client

# Initialize HTTPBearer and Supabase client
security = HTTPBearer()
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None
):
    """
    If USE_DUMMY_USER=true is set in the environment, return a dummy premium user.
    Otherwise, perform normal Supabase JWT validation and profile lookup.
    """

    # 1) If dummy mode is enabled, short-circuit and return a fake premium user.
    if os.getenv("USE_DUMMY_USER", "false").lower() == "true":
        return {
            "id":   "00000000-0000-0000-0000-000000000000",  # Dummy UUID
            "tier": "premium"
        }

    # 2) In non-dummy mode, enforce HTTPBearer auth. Manually call the security dependency:
    if credentials is None:
        # No credentials were passed in, so re-run the HTTPBearer dependency to raise the proper error:
        credentials = security.__call__(None)  # type: ignore

    # 3) Now that we have credentials, ensure it’s a Bearer token
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme."
        )

    jwt_token = credentials.credentials

    # 4) Validate JWT with Supabase Auth
    user_resp = supabase.auth.api.get_user(jwt_token)
    if user_resp.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )

    # 5) Look up the user's tier in your profiles table
    profile_resp = (
        supabase
        .table("profiles")
        .select("id,tier")
        .eq("id", user_resp.user.id)
        .single()
        .execute()
    )

    if profile_resp.error or profile_resp.data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile."
        )

    return {
        "id":   profile_resp.data["id"],
        "tier": profile_resp.data["tier"]
    }
