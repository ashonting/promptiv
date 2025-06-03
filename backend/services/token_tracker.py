# backend/services/token_tracker.py

# In-memory store; replace with DB in production
_user_token_usage = {}

def add_tokens_for_user(username, tokens):
    if username not in _user_token_usage:
        _user_token_usage[username] = 0
    _user_token_usage[username] += tokens

def get_tokens_for_user(username):
    return _user_token_usage.get(username, 0)
