# lib/costs.py
from config import MODEL_PRICES_USD

def estimate_chat_cost_usd(model: str, prompt_tokens: int, completion_tokens: int):
    """Chat料金（USD）を概算。価格未設定モデルは None。"""
    p = MODEL_PRICES_USD.get(model)
    if not p or p["in"] is None or p["out"] is None:
        return None
    return round((prompt_tokens * p["in"] + completion_tokens * p["out"]) / 1_000_000, 6)
