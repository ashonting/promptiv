# backend/routers/paddle.py

from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user
from backend.services.paddle_service import generate_checkout_link, generate_manage_link

router = APIRouter()

@router.post("/api/paddle/checkout-link")
def get_checkout_link(user=Depends(get_current_user)):
    user_email = user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Email required for checkout")
    url = generate_checkout_link(user_email)
    return {"url": url}

@router.post("/api/paddle/manage-link")
def get_manage_link(user=Depends(get_current_user)):
    sub_id = user.get("paddle_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No subscription id")
    url = generate_manage_link(sub_id)
    return {"url": url}
