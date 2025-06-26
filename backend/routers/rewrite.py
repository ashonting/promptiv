import logging
from fastapi import APIRouter, HTTPException, Depends, Request, status

from backend.models.rewrite_models import PromptRequest, PromptResponse, Variant
from backend.services.rewrite_service import rewrite_prompt_service
from backend.services.user_service import (
    get_or_create_user_by_device,
    ensure_user_exists_by_id,
    get_user_quota_info,
    increment_quota,
    get_user_by_id,
)
from backend.auth import get_optional_user

# --- Logger Setup ---
logger = logging.getLogger("promptiv.routers.rewrite")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter()

@router.post("/api/rewrite", response_model=PromptResponse)
def rewrite_prompt(
    prompt_request: PromptRequest,
    request: Request,
    user=Depends(get_optional_user)
) -> PromptResponse:
    """
    Accepts either an authenticated user or a device_hash for anonymous trial.
    - Checks quota and increments after usage.
    - Returns list of rewrite variants.
    """
    # --- Authenticate & Quota Flow ---
    if user:
        user_id = user["id"]
        ensure_user_exists_by_id(user_id, email=user.get("email"))
        quota = get_user_quota_info(user_id)
        if quota["quota_used"] >= quota["quota_total"]:
            logger.info(f"User {user_id} has exhausted their quota")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You’ve reached your limit for this plan. Upgrade or wait for your quota to reset."
            )
        result = rewrite_prompt_service(prompt_request, user_id, user.get("tier", "basic"))
        increment_quota(user_id)

    else:
        device_hash = prompt_request.device_hash
        if not device_hash:
            logger.warning("Missing credentials: neither user nor device_hash provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please sign up or provide a device hash."
            )
        anon = get_or_create_user_by_device(device_hash)
        user_id = anon["id"]
        quota = get_user_quota_info(user_id)
        if quota["quota_used"] >= quota["quota_total"]:
            logger.info(f"Device {device_hash} has exhausted its free trial")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You’ve used your free trial on this device. Sign up to continue!"
            )
        result = rewrite_prompt_service(prompt_request, user_id, anon.get("tier", "anonymous"))
        increment_quota(user_id)

    # --- Build standardized response ---
    raw = result.get("results") or result.get("variants") or []
    variants_data = []
    for v in raw:
        variants_data.append(
            Variant(
                variant_style=v.get("variant_style"),
                prompt=v.get("prompt"),
                best_llm=v.get("recommended_llm") or v.get("best_llm"),
                quick_copy_url=v.get("quick_copy_url"),
                best_for=v.get("best_for"),
                clarity=v.get("clarity"),
                complexity=v.get("complexity"),
                why_this_works=v.get("why_this_works"),
            )
        )

    response = PromptResponse(
        input=prompt_request.prompt,
        model=result.get("model"),
        variants=variants_data,
    )
    logger.info(f"Returned {len(variants_data)} variants for user {user_id}")
    return response
