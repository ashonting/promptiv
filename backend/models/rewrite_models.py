# backend/models/rewrite_models.py

from pydantic import BaseModel, Field
from typing import List, Optional


class Variant(BaseModel):
    variant_style: str = Field(
        ...,
        description="Style or type of this rewrite variant, e.g., 'Concise', 'Creative', 'Analytical'"
    )
    prompt: str = Field(
        ...,
        description="The rewritten prompt text for this variant"
    )
    best_llm: Optional[str] = Field(
        None,
        description="The recommended LLM for this variant"
    )
    quick_copy_url: Optional[str] = Field(
        None,
        description="URL to quickly open this variant in the LLM interface"
    )
    why_this_works: Optional[str] = Field(
        None,
        description="One‐sentence rationale for why this rewrite is valuable"
    )

    # ← NEW FIELDS ↓
    best_for: Optional[str]    = Field(
        None,
        description="Which LLM or use‐case this variant is best for"
    )
    clarity:  Optional[int]    = Field(
        None,
        description="Clarity rating (1–10)"
    )
    complexity: Optional[int]   = Field(
        None,
        description="Complexity rating (1–10)"
    )


class PromptRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="The user's original prompt to be rewritten"
    )
    device_hash: Optional[str] = Field(
        None,
        description="Device hash for anonymous quota flow"
    )


class PromptResponse(BaseModel):
    input: str = Field(
        ...,
        description="The user's original input prompt"
    )
    model: str = Field(
        ...,
        description="The LLM model chosen for rewriting"
    )
    variants: List[Variant] = Field(
        ...,
        description="List of rewrite variants returned by the service"
    )
