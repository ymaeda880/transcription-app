# pages/01_文字起こし.py
import time
import requests
import streamlit as st

from config import get_openai_api_key, OPENAI_TRANSCRIBE_URL, WHISPER_PRICE_PER_MIN
from lib.audio import get_audio_duration_seconds
from ui.sidebar import init_metrics_state, render_sidebar

st.set_page_config(page_title="01 文字起こし — Whisper", layout="wide")
st.title("① 文字起こし（Whisper API）")

# 初期化
init_metrics_state()
OPENAI_API_KEY = get_openai_api_key()
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY が .streamlit/secrets.toml に設定されていません。")
    st.stop()

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    uploaded = st.file_uploader(
        "音声ファイル（.wav / .mp3 / .m4a / .webm / .ogg 等）",
        type=["wav", "mp3", "m4a", "webm", "ogg"],
        accept_multiple_files=False,
    )
    fmt = st.selectbox("返却形式（response_format）", ["json", "text", "srt", "vtt"], index=0)
    language = st.text_input("言語コード（未指定なら自動判定）", value="ja")
    go = st.button("文字起こしを実行", type="primary", use_container_width=True)

with col_right:
    st.caption("結果")
    out_area = st.empty()

if go:
    if not uploaded:
        st.warning("先に音声ファイルをアップロードしてください。")
    else:
        # 音声長推定（料金用）
        audio_sec = get_audio_duration_seconds(uploaded)
        audio_min = audio_sec / 60.0 if audio_sec else None

        t0 = time.perf_counter()
        with st.spinner("Whisper API に送信中…"):
            file_bytes = uploaded.read()
            files = {"file": (uploaded.name, file_bytes, uploaded.type or "application/octet-stream")}
            #data = {"model": "whisper-1", "response_format": fmt}
            data = {
                "model": "whisper-1",
                "response_format": fmt,
                # 👇ここでプロンプトを渡す
                "prompt": "音声には『括弧1』『括弧2』『肩括弧1』などが含まれます。括弧の時は必ず数字を丸括弧付きで表記してください。例： (1), (2), (3)…．。また肩括弧の時は必ず数字を肩括弧付きで表記してください。例： 1), 2), 3)…．"
    }
            if language.strip():
                data["language"] = language.strip()
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            resp = requests.post(OPENAI_TRANSCRIBE_URL, headers=headers, files=files, data=data, timeout=600)
        elapsed = time.perf_counter() - t0

        if not resp.ok:
            st.error(f"APIエラー: {resp.status_code}\n{resp.text}")
        else:
            text = resp.json().get("text", "") if fmt == "json" else resp.text
            out_area.text_area("テキスト", value=text, height=350)
            st.session_state["transcribed_text"] = text

            # 本文メトリクス
            c1, c2, c3 = st.columns(3)
            c1.metric("処理時間", f"{elapsed:.2f} 秒")
            if audio_min is not None:
                usd = audio_min * WHISPER_PRICE_PER_MIN
                jpy = usd * float(st.session_state.get("usd_jpy", 150.0))
                c2.metric("概算料金 (USD)", f"${usd:,.6f}")
                c3.metric("概算料金 (JPY)", f"¥{jpy:,.2f}")
                st.session_state["metrics"]["whisper_cost_usd"] = usd
            else:
                c2.metric("概算料金 (USD)", "—")
                c3.metric("概算料金 (JPY)", "—")
                st.info("音声長の推定に失敗しました。`pip install mutagen audioread` を推奨。")

            st.session_state["metrics"]["whisper_time"] = elapsed

# 繋ぎ（②へ引き継ぐ）
if st.session_state.get("transcribed_text"):
    st.info("👇 下のボタンで議事録タブへテキストを引き継げます。")
    with st.expander("直近の文字起こし（確認用）", expanded=False):
        st.text_area("文字起こしテキスト（抜粋）",
                     value=st.session_state["transcribed_text"][:2000], height=160)
    if st.button("② 議事録タブへ引き継ぐ", type="primary", use_container_width=True):
        st.session_state["minutes_source_text"] = st.session_state["transcribed_text"]
        st.success("引き継ぎました。上部タブ『② 議事録作成（Markdown）』を開いてください。")

# サイドバー
render_sidebar()
