"""Compose destination base_catch + optional route override into one display string."""
from typing import Optional


def compose(base: Optional[str], route: Optional[str]) -> Optional[str]:
    parts = [p.strip() for p in (base, route) if p and p.strip()]
    return " ".join(parts) if parts else None
