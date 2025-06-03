import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# --- Load OpenAI API key ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("The OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)

# --- Supabase client for logging ---
from supabase import create_client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# --- Cost per 1k tokens for each LLM (update as needed) ---
MODEL_PRICING = {
    "GPT-4o": 0.005,
    "Claude 3 Opus": 0.015,
    "Claude 4 Sonnet": 0.008,
    "Claude 3 Haiku": 0.003,
    "Gemini 1.5 Pro": 0.004,
    "Perplexity Sonar": 0.002,
    "DeepSeek-V2": 0.002,
    "Cohere Command R": 0.004,
    "Llama 3": 0.002,
    "Mixtral": 0.002,
    "Whisper": 0.002,       # Placeholder
    "Google Veo": 0.002,    # Placeholder
    "Suno": 0.002,          # Placeholder
}

LLM_MAP = {
    "general chat": "GPT-4o",
    "personal assistant": "Claude 4 Sonnet",
    "life advice": "Claude 3 Opus",
    "productivity tips": "Claude 4 Sonnet",
    "motivation & coaching": "Claude 4 Sonnet",
    "creative writing": "Claude 3 Opus",
    "business writing": "Claude 4 Sonnet",
    "technical writing": "GPT-4o",
    "essay": "Claude 3 Opus",
    "storytelling": "Claude 3 Opus",
    "resume writing": "Claude 4 Sonnet",
    "cover letter": "Claude 4 Sonnet",
    "email drafting": "GPT-4o",
    "marketing copy": "Claude 3 Opus",
    "social media posts": "Claude 4 Sonnet",
    "press release": "Claude 3 Opus",
    "ad copy": "Claude 3 Opus",
    "poetry": "Claude 3 Opus",
    "code generation": "GPT-4o",
    "debugging": "GPT-4o",
    "creative coding": "Claude 3 Opus",
    "spreadsheet formulas": "GPT-4o",
    "api integration": "GPT-4o",
    "devops/scripting": "GPT-4o",
    "data analysis": "DeepSeek-V2",
    "data visualization": "Gemini 1.5 Pro",
    "math problem solving": "DeepSeek-V2",
    "technical Q&A": "GPT-4o",
    "prompt engineering": "GPT-4o",
    "research": "Gemini 1.5 Pro",
    "market research": "Gemini 1.5 Pro",
    "competitive analysis": "Gemini 1.5 Pro",
    "academic research": "Gemini 1.5 Pro",
    "summarization": "Gemini 1.5 Pro",
    "web search Q&A": "Perplexity Sonar",
    "up-to-date news": "Perplexity Sonar",
    "trend analysis": "Perplexity Sonar",
    "document search": "Cohere Command R",
    "pdf summarization": "Cohere Command R",
    "multimodal (vision)": "GPT-4o",
    "image captioning": "Gemini 1.5 Pro",
    "image analysis": "GPT-4o",
    "image OCR": "GPT-4o",
    "image understanding": "GPT-4o",
    "diagram generation": "Gemini 1.5 Pro",
    "translation": "Gemini 1.5 Pro",
    "language learning": "Claude 4 Sonnet",
    "lesson plan": "Claude 3 Opus",
    "SAT/ACT tutoring": "GPT-4o",
    "career coaching": "Claude 4 Sonnet",
    "personal finance Q&A": "Claude 4 Sonnet",
    "legal research": "Cohere Command R",
    "medical research": "Gemini 1.5 Pro",
    "health & wellness Q&A": "Gemini 1.5 Pro",
    "audio transcription": "Whisper",
    "audio summarization": "Whisper",
    "video analysis": "Google Veo",  # placeholder
    "music generation": "Suno",       # placeholder
    "contract analysis": "Cohere Command R",
    "policy review": "Cohere Command R",
    "compliance check": "Cohere Command R",
    "enterprise search": "Cohere Command R",
    "fast/simple answer": "Mixtral",
    "low-cost answer": "Mixtral",
    "quick brainstorming": "Llama 3",
    "meta-prompting": "Claude 3 Opus",
    "reflection & feedback": "Claude 3 Opus",
    "creative brainstorming": "Claude 3 Opus",
}

LLM_CHAT_URLS = {
    "Claude 3 Opus": "https://claude.ai/chats",
    "Claude 4 Sonnet": "https://claude.ai/chats",
    "Claude 3 Haiku": "https://claude.ai/chats",
    "GPT-4o": "https://chat.openai.com/",
    "Gemini 1.5 Pro": "https://gemini.google.com/app",
    "Perplexity Sonar": "https://www.perplexity.ai/",
    "DeepSeek-V2": "https://platform.deepseek.com/",
    "Cohere Command R": "https://console.cohere.com/",
    "Llama 3": "https://llama.meta.com/",
    "Mixtral": "https://chat.mistral.ai/",
    "Whisper": "https://platform.openai.com/playground/whisper",
    "Google Veo": "https://veo.google.com/",
    "Suno": "https://app.suno.ai/",
}

VARIANT_DEFINITIONS = {
    "Concise": {
        "best_for": "Sharpening your request. Direct, unambiguous prompts for fast, focused AI output.",
        "clarity": "high",
        "complexity": "low",
        "system": lambda prompt, llm: (
            "Rewrite the following prompt to be as clear, direct, and effective as possible for an AI model. "
            "Strip out any ambiguity or extra fluff. Focus only on what is needed to get a precise, actionable answer. "
            "Respond in this format:\n"
            "Improved Prompt: <insert improved prompt>\n"
            "Why this works: <insert one-line rationale for why this prompt is now stronger>"
        ),
    },
    "Creative": {
        "best_for": "Unlocking new angles and perspectives that only AI can discover—get insights a human expert wouldn’t even imagine.",
        "clarity": "high",
        "complexity": "medium",
        "system": lambda prompt, llm: (
            "Rewrite the user's prompt so it leverages the full power of advanced AI, producing a version that a human could not easily generate. "
            "Approach the prompt from a novel, expert, or overlooked angle to extract new value or insight, but keep it practical and relevant—never whimsical or fantasy-based. "
            "Use AI’s unique ability to analyze, combine, or reframe information beyond human limits. "
            "Respond in this format:\n"
            "Improved Prompt: <insert improved prompt>\n"
            "Why this works: <insert one-line rationale for why this prompt leverages AI in a unique way>"
        ),
    },
    "Analytical": {
        "best_for": "Structuring complex questions. Breaks big requests into actionable sub-questions or logical steps.",
        "clarity": "high",
        "complexity": "medium",
        "system": lambda prompt, llm: (
            "Rewrite the user's prompt to guide the AI to break down the task into logical, actionable steps or sub-questions for a comprehensive response. "
            "Do not answer the prompt; only rewrite it to maximize detailed, structured output. "
            "Respond in this format:\n"
            "Improved Prompt: <insert improved prompt>\n"
            "Why this works: <insert one-line rationale for why this prompt will get a more thorough answer>"
        ),
    }
}

def log_prompt_history(
    user_id,
    input_prompt,
    variants,
    prompt_tokens=None,
    completion_tokens=None,
    total_tokens=None,
    cost=None,
    status=None,
    classification=None,
    best_llm=None,
    plan=None,
    user_agent=None,
    ip_address=None,
    latency_ms=None,
    error_message=None
):
    """
    Logs a prompt history record to Supabase. All non-required fields are optional.
    """
    try:
        data = {
            "user_id": user_id,
            "input": input_prompt,
            "variants": variants,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "status": status,
            "classification": classification,
            "best_llm": best_llm,
            "plan": plan,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "latency_ms": latency_ms,
            "error_message": error_message
        }
        # Only send fields that are not None
        data = {k: v for k, v in data.items() if v is not None}
        result = supabase.table("prompt_history").insert(data).execute()
        if result.data and isinstance(result.data, list) and "id" in result.data[0]:
            return result.data[0]["id"]
        return None
    except Exception as e:
        print(f"Supabase logging failed: {e}")
        return None

def log_token_usage(
    user_id, model, prompt_tokens, completion_tokens, total_tokens, cost, status="success", history_id=None
):
    try:
        data = {
            "user_id": user_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "status": status
        }
        if history_id:
            data["history_id"] = history_id
        supabase.table("token_usage").insert(data).execute()
    except Exception as e:
        print(f"Supabase token usage logging failed: {e}")

def classify_prompt_task(prompt):
    task_types = sorted(list(set(LLM_MAP.keys())))
    models = sorted(list(set(LLM_MAP.values())))

    SYSTEM_PROMPT = (
        "You are a prompt intent classifier. "
        "Given a user prompt, classify its primary task type from the following options:\n"
        f"{', '.join(task_types)}.\n"
        "Then, based on the current industry consensus (June 2025), recommend the best LLM from this list:\n"
        f"{', '.join(models)}.\n"
        "Respond ONLY as valid JSON in this format:\n"
        '{ "task_type": "<task type>", "best_llm": "<model>", "rationale": "<brief explanation>" }'
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=220
        )
        content = response.choices[0].message.content
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace != -1:
            content = content[first_brace:last_brace+1]
        data = json.loads(content)
        return data
    except Exception as e:
        return {
            "task_type": "general",
            "best_llm": "GPT-4o",
            "rationale": f"Default fallback. Error: {e}"
        }

def parse_improved_prompt(raw_content):
    improved = ""
    why = ""
    for line in raw_content.splitlines():
        l = line.lower()
        if l.startswith("improved prompt:"):
            improved = line.split(":", 1)[1].strip()
        elif l.startswith("why this works:"):
            why = line.split(":", 1)[1].strip()
    return improved, why

def rewrite_with_llm(prompt, variant_style, best_llm, rationale):
    vdef = VARIANT_DEFINITIONS[variant_style]
    sys_prompt = vdef["system"](prompt, best_llm)
    tokens_used = 0
    prompt_tokens = 0
    completion_tokens = 0
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85 if variant_style == "Creative" else 0.65,
            max_tokens=400
        )
        raw_content = response.choices[0].message.content.strip()
        improved_prompt, why_this_works = parse_improved_prompt(raw_content)
        if not improved_prompt:
            improved_prompt = "Rewritten for clarity and effectiveness, but specific improvement not returned."
        if not why_this_works:
            why_this_works = "This prompt is more effective for LLMs based on clarity, structure, or creative perspective."
        if hasattr(response, "usage") and response.usage is not None:
            prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
            completion_tokens = getattr(response.usage, "completion_tokens", 0)
            tokens_used = getattr(response.usage, "total_tokens", 0)
    except Exception as e:
        improved_prompt = "We were unable to generate this variant due to a technical issue."
        why_this_works = "A fallback version is shown."
    return {
        "variant_style": variant_style,
        "best_for": vdef["best_for"],
        "clarity": vdef["clarity"],
        "complexity": vdef["complexity"],
        "prompt": improved_prompt,
        "why_this_works": why_this_works,
        "recommended_llm": best_llm,
        "llm_rationale": rationale,
        "quick_copy_url": LLM_CHAT_URLS.get(best_llm, ""),
        "tokens_used": tokens_used,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def rewrite_prompt(prompt_request, user):
    import json
    prompt = prompt_request["prompt"] if isinstance(prompt_request, dict) else getattr(prompt_request, "prompt", "")
    log_status = "success"
    cost = None
    try:
        intent = classify_prompt_task(prompt)
        best_llm = intent.get("best_llm", "GPT-4o")
        rationale = intent.get("rationale", "")

        VARIANT_STYLES = ["Concise", "Creative", "Analytical"]
        variants = []
        total_tokens = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for style in VARIANT_STYLES:
            variant = rewrite_with_llm(prompt, style, best_llm, rationale)
            total_tokens += variant.get("tokens_used", 0) or 0
            total_prompt_tokens += variant.get("prompt_tokens", 0) or 0
            total_completion_tokens += variant.get("completion_tokens", 0) or 0
            variants.append(variant)

        price_per_1k = MODEL_PRICING.get(best_llm, 0.005)
        cost = round((total_tokens / 1000) * price_per_1k, 6)

        result = {
            "variants": variants,
            "classification": intent,
        }
    except Exception as e:
        result = {
            "variants": [],
            "classification": {},
        }
        log_status = f"error: {str(e)}"
        total_tokens = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0

    # Log prompt history (get history_id for usage tracking)
    history_id = None
    try:
        history_id = log_prompt_history(
            user.get("id"),                                  # user_id
            prompt,                                          # input
            json.dumps(result.get("variants", [])),          # variants
            total_prompt_tokens,                             # prompt_tokens
            total_completion_tokens,                         # completion_tokens
            total_tokens,                                    # total_tokens
            cost,                                            # cost
            log_status,                                      # status
            json.dumps(result.get("classification", {})),    # classification
            best_llm,                                        # best_llm
            user.get("tier"),                                # plan
            user.get("user_agent"),                          # user_agent
            user.get("ip_address"),                          # ip_address
            None,                                            # latency_ms
            None                                             # error_message
        )
    except Exception as e:
        print(f"Supabase prompt history logging failed: {e}")

    # Log token usage
    try:
        log_token_usage(
            user.get("id"),
            best_llm,
            total_prompt_tokens,
            total_completion_tokens,
            total_tokens,
            cost,
            log_status,
            history_id=history_id
        )
    except Exception as e:
        print(f"Supabase token usage logging failed: {e}")

    return result
