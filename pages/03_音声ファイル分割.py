import io
import math
import zipfile
from datetime import timedelta

import streamlit as st
from pydub import AudioSegment

st.set_page_config(page_title="MP3 分割ツール（オーバーラップ付き）", page_icon="🎧", layout="centered")
st.title("🎧 MP3 分割ツール（オーバーラップ付き）")

st.write(
    "アップロードした MP3 を一定長さで分割し、隣接チャンクに重なり（オーバーラップ）をつけます。"
    "文字起こし（transcription）前の前処理にどうぞ。"
)

with st.sidebar:
    st.header("設定")
    chunk_min = st.selectbox("チャンク長（分）", [3, 5, 10, 15, 20, 30], index=1)
    overlap_min = st.number_input("オーバーラップ（分）", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
    target_bitrate = st.selectbox("書き出しビットレート", ["原則そのまま/自動", "128k", "160k", "192k", "256k", "320k"], index=2)
    fade_ms = st.number_input("フェード（クリックノイズ低減, ms）", min_value=0, max_value=2000, value=0, step=100)
    min_tail_keep = st.checkbox("最後の“短すぎる尻尾”は前チャンクに吸収（重複を増やさない）", value=True)

uploaded = st.file_uploader("MP3 ファイルをアップロード", type=["mp3"])

def hhmmss(ms: int) -> str:
    return str(timedelta(milliseconds=ms)).split(".")[0]

def split_with_overlap(audio: AudioSegment, chunk_ms: int, overlap_ms: int, fade_ms: int, absorb_tiny_tail: bool):
    """
    overlap を含めて分割。最後の短すぎる尻尾は吸収（オプション）。
    戻り値: list[dict] with keys {start_ms, end_ms, segment(AudioSegment)}
    """
    results = []
    n = len(audio)

    if chunk_ms <= 0:
        raise ValueError("chunk_ms must be > 0")
    step = max(1, chunk_ms - overlap_ms)  # 次の開始位置

    start = 0
    while start < n:
        end = min(start + chunk_ms, n)
        seg = audio[start:end]

        # 短すぎる最後の尻尾（例： overlap 以下）を、前チャンクに吸収して重複を増やさない
        if absorb_tiny_tail and start > 0 and end == n:
            tail_len = end - start
            if tail_len < overlap_ms:
                # 直前のチャンクを拡張する（すでに push 済み）
                prev = results[-1]
                prev_end = prev["end_ms"]
                # 直前の終端が今回の開始= start のはず。終端を末尾まで伸ばす
                prev["end_ms"] = n
                prev["segment"] = audio[prev["start_ms"]:n]
                break

        # フェード（任意）
        if fade_ms > 0 and len(seg) > fade_ms * 2:
            seg = seg.fade_in(fade_ms).fade_out(fade_ms)

        results.append({"start_ms": start, "end_ms": end, "segment": seg})

        if end == n:
            break
        start += step

    return results

if uploaded is not None:
    try:
        # 1) 読み込み
        audio = AudioSegment.from_file(uploaded, format="mp3")

        # 2) パラメータ（ms）
        chunk_ms = int(chunk_min * 60_000)
        overlap_ms = int(overlap_min * 60_000)

        if overlap_ms >= chunk_ms:
            st.error("オーバーラップはチャンク長未満にしてください。")
        else:
            # 3) 分割
            parts = split_with_overlap(
                audio=audio,
                chunk_ms=chunk_ms,
                overlap_ms=overlap_ms,
                fade_ms=fade_ms,
                absorb_tiny_tail=min_tail_keep,
            )

            # 4) プレビュー（一覧）
            st.subheader("分割プレビュー")
            rows = []
            for i, p in enumerate(parts):
                rows.append(
                    {
                        "Part": i,
                        "Start": hhmmss(p["start_ms"]),
                        "End": hhmmss(p["end_ms"]),
                        "Duration": hhmmss(p["end_ms"] - p["start_ms"]),
                    }
                )
            st.dataframe(rows, hide_index=True, use_container_width=True)

            # 5) ZIP 作成（メモリ）
            base_name = (uploaded.name.rsplit(".", 1)[0] or "audio").replace(" ", "_")
            mem_zip = io.BytesIO()
            bitrate_arg = None if "自動" in target_bitrate else target_bitrate  # None なら pydub/ffmpeg に任せる

            with zipfile.ZipFile(mem_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for i, p in enumerate(parts):
                    start_tag = hhmmss(p["start_ms"]).replace(":", "")
                    end_tag = hhmmss(p["end_ms"]).replace(":", "")
                    filename = f"{base_name}_part{i:03d}_{start_tag}-{end_tag}.mp3"

                    buf = io.BytesIO()
                    export_kwargs = {"format": "mp3"}
                    if bitrate_arg:
                        export_kwargs["bitrate"] = bitrate_arg
                    p["segment"].export(buf, **export_kwargs)
                    zf.writestr(filename, buf.getvalue())

                # 透過用のインデックス（CSV）も同梱
                import csv
                index_csv = io.StringIO()
                writer = csv.writer(index_csv)
                writer.writerow(["part", "start_ms", "end_ms", "start_hhmmss", "end_hhmmss"])
                for i, p in enumerate(parts):
                    writer.writerow([i, p["start_ms"], p["end_ms"], hhmmss(p["start_ms"]), hhmmss(p["end_ms"])])
                zf.writestr(f"{base_name}_index.csv", index_csv.getvalue().encode("utf-8"))

            mem_zip.seek(0)
            st.download_button(
                "📦 分割済みMP3をZIPでダウンロード",
                data=mem_zip,
                file_name=f"{base_name}_split_overlap.zip",
                mime="application/zip",
            )

            st.success(f"作成チャンク数: {len(parts)}  | 総再生時間: {hhmmss(len(audio))}")

    except Exception as e:
        st.error(f"処理中にエラーが発生しました: {e}")

else:
    st.info("左の設定を選び、MP3ファイルをアップロードしてください。")
