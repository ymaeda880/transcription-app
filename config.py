# config.py
import streamlit as st

# OpenAI API
OPENAI_TRANSCRIBE_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

def get_openai_api_key() -> str:
    return st.secrets.get("OPENAI_API_KEY", "")

# 価格（USD / 100万トークン）
MODEL_PRICES_USD = {
    "gpt-4o-mini":  {"in": 0.60, "out": 2.40},
    "gpt-4o":       {"in": None, "out": None},
    "gpt-4.1-mini": {"in": None, "out": None},
    "gpt-4.1":      {"in": None, "out": None},
    "gpt-3.5-turbo":{"in": None, "out": None},
}

# Whisper（USD / 分）
WHISPER_PRICE_PER_MIN = 0.006

# 為替の初期値（secretsにUSDJPYがあれば上書き）
DEFAULT_USDJPY = float(st.secrets.get("USDJPY", 150.0))
