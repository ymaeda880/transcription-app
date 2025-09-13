streamlit run app.py

pip install -r requirements.txt

brew install ffmpeg

your-app/
├─ app.py # ホーム（設定・使い方）
├─ requirements.txt
├─ config.py # API エンドポイント・価格・為替初期値・API キー取得
├─ lib/
│ ├─ **init**.py
│ ├─ audio.py # 音声長推定（mutagen → wave → audioread）
│ └─ costs.py # 料金計算（Chat の USD 概算）
├─ ui/
│ ├─ **init**.py
│ └─ sidebar.py # サイドバー描画 & state 初期化
└─ pages/
├─ 01*文字起こし.py # Whisper ページ（USD/JPY 表示）
└─ 02*議事録作成.py # 議事録ページ（USD/JPY 表示）
