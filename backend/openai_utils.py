import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("The OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)

# LLM mapping (update as needed)
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

def classify_prompt_task(prompt):
    """Use GPT-4o to classify prompt intent and best LLM."""
    SYSTEM_PROMPT = (
        "You are a prompt intent classifier. "
        "Given a user prompt, classify its primary task type from the following options: "
        "'creative writing', 'business writing', 'essay', 'long-form', 'storytelling', 'technical Q&A', "
        "'coding', 'code generation', 'multimodal', 'brainstorming', 'summarization', 'research', 'analysis', "
        "'quick/simple'. "
        "Then, based on June 2025 industry consensus, recommend the best LLM: 'Claude 3 Opus', 'GPT-4o', "
        "'Gemini 1.5', or 'Mixtral'. Respond as JSON: "
        "{ \"task_type\": \"creative writing\", \"best_llm\": \"Claude 3 Opus\", \"rationale\": \"Claude 3 Opus is best for creative writing and long-form output.\" }"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=200
    )
    content = response.choices[0].message.content
    try:
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace != -1:
            content = content[first_brace:last_brace+1]
        data = json.loads(content)
        return data
    except Exception:
        return {
            "task_type": "general",
            "best_llm": "GPT-4o",
            "rationale": "Default fallback."
        }

def rewrite_with_llm(prompt, variant_style, best_llm, rationale):
    """Generate a rewritten prompt optimized for the given LLM and variant style."""
    SYSTEM_PROMPT = f"""
You are an expert AI prompt engineer. Your job is to rewrite user prompts for maximum effectiveness in a specific LLM and thinking style.
You MUST follow these instructions:

- Do NOT merely rephrase; significantly transform the prompt for clarity, context, and AI effectiveness.
- Your rewrite MUST be explicitly optimized for the following LLM: {best_llm}.
- State the task in the user's perspective (use "I" or "my", not "you" or "your").
- The prompt should be ready to paste into {best_llm}.
- Use the following variant style: "{variant_style}".
- Briefly summarize the intended application ("best_for"), clarity, and complexity (e.g. 'drafting blog posts | high clarity | low complexity').
- After the prompt, add a concise 'Why this works:' explanation, referencing the LLM's specific strengths and the rewrite's improvements.

If helpful, here are the current industry strengths:
Claude 3 Opus: creative, long-form, business writing, nuanced language
GPT-4o: technical Q&A, code, logic, concise answers, versatile
Gemini 1.5: research, summarization, analysis, web context
Mixtral: speed, simple summarization, low cost

Format your reply as JSON (no markdown, no explanations):
{{
  "variant_style": "<style>",
  "best_for": "<intended application or user>",
  "clarity": "<high|medium|low>",
  "complexity": "<high|medium|low>",
  "prompt": "<final rewritten prompt, first-person tone>",
  "why_this_works": "<explanation tailored to {best_llm}>",
  "recommended_llm": "{best_llm}",
  "llm_rationale": "{rationale}"
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.85 if variant_style == "Creative" else 0.65,
        max_tokens=400
    )
    content = response.choices[0].message.content
    try:
        first_brace = content.find("{")
        last_brace = content.rfind("}")
        if first_brace != -1 and last_brace != -1:
            content = content[first_brace:last_brace+1]
        data = json.loads(content)
        return data
    except Exception as e:
        return {
            "variant_style": variant_style,
            "best_for": "",
            "clarity": "",
            "complexity": "",
            "prompt": "[Error generating prompt.]",
            "why_this_works": str(e),
            "recommended_llm": best_llm,
            "llm_rationale": rationale
        }

def rewrite_prompt(prompt_request, user):
    prompt = prompt_request.prompt if hasattr(prompt_request, "prompt") else prompt_request["prompt"]

    # 1. Classify the prompt
    intent = classify_prompt_task(prompt)
    best_llm = intent.get("best_llm", "GPT-4o")
    rationale = intent.get("rationale", "")

    # 2. Define variant styles
    VARIANT_STYLES = ["Concise", "Creative", "Analytical"]

    variants = []
    for style in VARIANT_STYLES:
        variant = rewrite_with_llm(prompt, style, best_llm, rationale)
        variant["quick_copy_url"] = LLM_CHAT_URLS.get(best_llm, "")
        variants.append(variant)

    return {
        "variants": variants,
        "classification": intent,
    }
