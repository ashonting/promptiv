# backend/services/rewrite_service.py

import os
import re
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
from supabase import create_client

from backend.models.rewrite_models import PromptRequest

# --- Logging setup ---
logger = logging.getLogger("promptiv.rewrite_service")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Load env & init clients ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# --- Tier → model map ---
TIER_MODEL_MAP = {
    "anonymous": "gpt-3.5-turbo",
    "basic":     "gpt-3.5-turbo",
    "premium":   "gpt-4o",
    "pro":       "gpt-4o",
}

# --- Quick-open URL for each LLM (fallback "#") ---
LLM_URL_MAP = {
    "gpt-3.5-turbo": "https://chat.openai.com/?model=gpt-3.5-turbo",
    "gpt-4o":        "https://chat.openai.com/?model=gpt-4o",
}

# --- Static clarity/complexity scores per style ---
STYLE_SCORES = {
    "Concise":    {"clarity": 9, "complexity": 4},
    "Analytical": {"clarity": 8, "complexity": 7},
    "Creative":   {"clarity": 7, "complexity": 8},
}

# --- Instructions per style ---
STYLE_INSTRUCTIONS: Dict[str,str] = {
    "Concise": (
        "Rewrite the prompt into the most essential, direct form—one or two sentences max. "
        "Strip every non-critical word; focus only on core intent."
    ),
    "Analytical": (
        "Rewrite the prompt as a logically structured outline or question. "
        "Keep it in the same form (question stays question, statement stays statement) "
        "so that it asks for step-by-step, reasoned insights without answering it."
    ),
    "Creative": (
        "Reframe the prompt with a fresh, AI-driven perspective that the user wouldn’t think of. "
        "Push boundaries—not random whimsy, but inspirational ideas or angles to spark imagination."
    )
}

def parse_ai_output(style: str, text: str) -> Dict[str,str]:
    """
    Parses the LLM output:
      - Extracts the rewritten prompt (under the style header)
      - Extracts the "Why this works:" rationale if present
    Falls back gracefully if formats differ.
    """
    # Normalize whitespace
    text = text.strip()
    # Extract "why" section
    why = "No explanation provided."
    why_token = "Why this works:"
    if why_token in text:
        parts = text.split(why_token, 1)
        main = parts[0].strip()
        why = parts[1].strip()
    else:
        main = text
    # Extract the rewrite
    # Look for a header like "Concise:" or "Concise Rewrite:" and capture everything after
    pattern = re.compile(rf"^{style}[^:]*:\s*(.*)$", re.IGNORECASE | re.DOTALL)
    match = pattern.search(main)
    if match:
        rewrite = match.group(1).strip()
    else:
        logger.warning(f"Could not find “{style}:” header – falling back to full block")
        rewrite = main

    return {"rewrite": rewrite, "why": why}

def rewrite_prompt_service(
    prompt_request: PromptRequest,
    user_id: str,
    user_tier: str = "basic"
) -> Dict[str,Any]:
    """
    Generates three variants (Concise, Analytical, Creative),
    attaches scores, logs to Supabase, and returns:
      {
        "input":   "...",
        "model":   "gpt-3.5-turbo",
        "results": [ { variant_style, prompt, best_llm, quick_copy_url,
                       why_this_works, best_for, clarity, complexity }, ... ]
      }
    """
    prompt_text = prompt_request.prompt.strip()
    model_name  = TIER_MODEL_MAP.get(user_tier.lower(), "gpt-3.5-turbo")
    now_iso     = datetime.utcnow().isoformat()

    variants = []
    tokens_p = tokens_c = 0

    for style in ("Concise", "Analytical", "Creative"):
        sys_msg = (
            f"You are an elite prompt engineer. Produce a {style.lower()} rewrite "
            f"for the user’s prompt exactly as instructed below. Then include "
            f"'Why this works:' with a one-sentence rationale.\n\n"
            f"{STYLE_INSTRUCTIONS[style]}"
        )

        try:
            resp = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role":"system","content": sys_msg},
                    {"role":"user",  "content": prompt_text}
                ],
                temperature=0.85 if style=="Creative" else 0.65,
                max_tokens=375,
            )
            ai_text = resp.choices[0].message.content.strip()
            usage  = getattr(resp, "usage", None)
            if usage:
                tokens_p += getattr(usage, "prompt_tokens", 0)
                tokens_c += getattr(usage, "completion_tokens", 0)
        except RateLimitError as e:
            logger.error(f"RateLimitError [{style}]: {e}")
            ai_text = "[Error: rate limited]"
        except APIError as e:
            logger.error(f"APIError [{style}]: {e}")
            ai_text = "[Error generating variant]"
        except Exception:
            logger.exception(f"Unexpected error [{style}]")
            ai_text = "[Unexpected error]"

        parsed = parse_ai_output(style, ai_text or "")
        scores = STYLE_SCORES.get(style, {})

        variants.append({
            "variant_style":   style,
            "prompt":          parsed["rewrite"],
            "best_llm":        model_name,
            "quick_copy_url":  LLM_URL_MAP.get(model_name, "#"),
            "why_this_works":  parsed["why"],
            "best_for":        model_name,
            "clarity":         scores.get("clarity"),
            "complexity":      scores.get("complexity"),
        })

    # Log to Supabase
    history_id = str(uuid.uuid4())
    try:
        supabase.table("prompt_history").insert({
            "id":                history_id,
            "user_id":           user_id,
            "input":             prompt_text,
            "variants":          variants,
            "prompt_tokens":     tokens_p or None,
            "completion_tokens": tokens_c or None,
            "total_tokens":      (tokens_p + tokens_c) or None,
            "created_at":        now_iso,
            "plan":              user_tier,
        }).execute()
    except Exception:
        logger.exception("Failed to log prompt_history")

    return {
        "input":   prompt_text,
        "model":   model_name,
        "results": variants
    }
