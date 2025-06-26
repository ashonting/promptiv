import os

def is_rewrite_gate_enabled() -> bool:
    # Default to False (testing mode) if not set
    val = os.getenv("REWRITE_GATE_ENABLED", "false").lower()
    return val in ("true", "1", "yes")
