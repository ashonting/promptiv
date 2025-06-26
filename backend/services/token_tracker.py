# backend/services/token_tracker.py

# Deprecated: All token tracking is now handled in Supabase prompt_history and token_usage tables.
# This module is retained for dev reference only.

def add_tokens_for_user(username, tokens):
    """No-op: Use Supabase for all production token tracking."""
    pass

def get_tokens_for_user(username):
    """No-op: Use Supabase for all production token tracking."""
    return 0
