# pages/02_議事録作成.py
import time
import requests
import streamlit as st

from config import get_openai_api_key, OPENAI_CHAT_URL
from lib.costs import estimate_chat_cost_usd
from ui.sidebar import init_metrics_state, render_sidebar

st.set_page_config(page_title="02 議事録作成 — Chat", layout="wide")
st.title("② 議事録作成（Markdown）")

# 初期化
init_metrics_state()
OPENAI_API_KEY = get_openai_api_key()
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY が .streamlit/secrets.toml に設定されていません。")
    st.stop()

default_prompt = """あなたは20年以上のキャリアがある議事録作成の専門家です。
以下の文字起こしテキストをもとに正式な議事録を作成し、その後、発言をそのままの形でまとめた逐語記録も出力してください。
"""

colA, colB = st.columns([1, 1], gap="large")

with colA:
    base_prompt = st.text_area("プロンプト（編集可）", value=default_prompt, height=260)
    extra = st.text_area("追加指示（任意）", value="", height=120)
    model = st.selectbox("モデル", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "gpt-3.5-turbo"], index=0)
    temperature = st.slider("温度（0=厳格 / 2=自由）", 0.0, 2.0, value=0.2, step=0.1)
    go_minutes = st.button("議事録を生成", type="primary", use_container_width=True)

with colB:
    src = st.text_area(
        "文字起こしテキスト",
        value=st.session_state.get("minutes_source_text", ""),
        height=440,
        placeholder="①ページで文字起こししたテキストを引き継ぐか、ここに貼り付けてください。",
    )

if go_minutes:
    if not src.strip():
        st.warning("文字起こしテキストを入力してください。")
    else:
        combined = base_prompt.strip()
        if extra.strip():
            combined += "\n\n【追加指示】\n" + extra.strip() + "\n"
        combined += "\n" + src

        t0 = time.perf_counter()
        with st.spinner("議事録を生成中…"):
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            body = {"model": model, "temperature": temperature, "max_tokens": 1200,
                    "messages": [{"role": "user", "content": combined}]}
            r = requests.post(OPENAI_CHAT_URL, headers=headers, json=body, timeout=600)
        elapsed = time.perf_counter() - t0

        if not r.ok:
            st.error(f"APIエラー: {r.status_code}\n{r.text}")
        else:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            st.markdown("### 📝 生成結果（Markdown 表示）")
            st.markdown(text)

            usage = data.get("usage", {}) or {}
            ptok = int(usage.get("prompt_tokens", 0))
            ctok = int(usage.get("completion_tokens", 0))
            usd = estimate_chat_cost_usd(model, ptok, ctok)
            jpy = usd * float(st.session_state.get("usd_jpy", 150.0)) if usd is not None else None

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("処理時間", f"{elapsed:.2f} 秒")
            c2.metric("入力トークン", f"{ptok:,}")
            c3.metric("出力トークン", f"{ctok:,}")
            c4.metric("概算料金 (USD)", f"${usd:,.6f}" if usd is not None else "—")
            c5.metric("概算料金 (JPY)", f"¥{jpy:,.2f}" if jpy is not None else "—")

            st.session_state["metrics"].update(
                chat_time=elapsed, chat_cost_usd=usd, ptok=ptok, ctok=ctok
            )

# サイドバー
render_sidebar()
