### File: backend/services/openai_utils.py

import os
import json
from openai import OpenAI, APIError, Timeout, RateLimitError
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("The OPENAI_API_KEY environment variable is not set.")

client = OpenAI(api_key=api_key)

LLM_MAP = {
    "creative writing": "Claude 3 Opus",
    "business writing": "Claude 3 Opus",
    "essay": "Claude 3 Opus",
    "long-form": "Claude 3 Opus",
    "storytelling": "Claude 3 Opus",
    "technical Q&A": "GPT-4o",
    "coding": "GPT-4o",
    "code generation": "GPT-4o",
    "multimodal": "GPT-4o",
    "brainstorming": "GPT-4o",
    "summarization": "Gemini 1.5",
    "research": "Gemini 1.5",
    "analysis": "Gemini 1.5",
    "quick/simple": "Mixtral",
}

LLM_CHAT_URLS = {
    "Claude 3 Opus": "https://claude.ai/chats",
    "GPT-4o": "https://chat.openai.com/",
    "Gemini 1.5": "https://gemini.google.com/app",
    "Mixtral": "https://chat.mistral.ai/",
}

def classify_prompt_task(prompt: str) -> dict:
    SYSTEM_PROMPT = (
        "You are a prompt intent classifier. Given a user prompt, classify its primary task..."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        content = response.choices[0].message.content
        json_str = content[content.find("{"):content.rfind("}")+1]
        return json.loads(json_str)
    except (Timeout, APIError, RateLimitError) as e:
        return {"task_type": "general", "best_llm": "GPT-4o", "rationale": str(e)}
    except Exception as e:
        return {"task_type": "general", "best_llm": "GPT-4o", "rationale": f"Unhandled: {str(e)}"}

def rewrite_with_llm(prompt: str, variant_style: str, best_llm: str, rationale: str) -> dict:
    SYSTEM_PROMPT = f"""
You are an expert AI prompt engineer... etc.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85 if variant_style == "Creative" else 0.65,
            max_tokens=400,
        )
        content = response.choices[0].message.content
        json_str = content[content.find("{"):content.rfind("}")+1]
        return json.loads(json_str)
    except (Timeout, APIError, RateLimitError) as e:
        return {
            "variant_style": variant_style,
            "prompt": "[Error generating prompt.]",
            "why_this_works": str(e),
            "recommended_llm": best_llm,
            "llm_rationale": rationale
        }
    except Exception as e:
        return {
            "variant_style": variant_style,
            "prompt": "[Unhandled error during generation]",
            "why_this_works": str(e),
            "recommended_llm": best_llm,
            "llm_rationale": rationale
        }

def rewrite_prompt(prompt_request: dict, user: dict, override_model: str = None) -> dict:
    prompt = prompt_request.get("prompt")
    intent = classify_prompt_task(prompt)
    best_llm = override_model or intent.get("best_llm", "GPT-4o")
    rationale = intent.get("rationale", "")
    styles = ["Concise", "Creative", "Analytical"]
    results = [rewrite_with_llm(prompt, s, best_llm, rationale) for s in styles]
    for r in results:
        r["quick_copy_url"] = LLM_CHAT_URLS.get(best_llm, "")
    return {"input": prompt, "model": best_llm, "results": results}
