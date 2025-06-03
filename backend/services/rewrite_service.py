# backend/services/rewrite_service.py

from backend.services.openai_utils import rewrite_prompt

def rewrite_prompt_service(prompt_request, user, plan="premium"):
    """
    Premium prompt rewrite with LLM-matching and variants.
    """
    return rewrite_prompt(prompt_request, user)
