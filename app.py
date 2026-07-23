import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import json
from datetime import datetime
from drive_utils import load_json_from_drive, save_json_to_drive

# ---------------------------------------------------------
# 1. ページ基本設定 & Gemini API 初期化 (新SDK形式)
# ---------------------------------------------------------
st.set_page_config(
    page_title="J.A.R.V.I.S. Health System",
    page_icon="🤖",
    layout="wide"
)

# Secrets から API Key を取得して Client を初期化
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"APIキーの設定エラー: {e}")
    st.stop()

# Interactions API 対応のモデル指定（動的最新モデル）
MODEL_NAME = "gemini-1.5-flash"

# ---------------------------------------------------------
# 2. Google Drive からデータの初期ロード
# ---------------------------------------------------------
DRIVE_MEMORY_FILE = "jarvis_memory.json"
DRIVE_NUTRITION_FILE = "nutrition_log.json"

# 会話履歴の初期化
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_json_from_drive(DRIVE_MEMORY_FILE, default_factory=list)

# 栄養ログの初期化
if "nutrition_log" not in st.session_state:
    st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)

# ---------------------------------------------------------
# 3. システムプロンプト（J.A.R.V.I.S.のペルソナ設定）
# ---------------------------------------------------------
SYSTEM_PROMPT = """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の健康・栄養管理をプロフェッショナルかつスマートにサポートしてください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
- ユーモアを交えつつも、データやアドバイスは的確かつ迅速に提示してください。

【機能】
1. 食事画像が送られた場合は、カロリーや主要栄養素（PFCバランスなど）を推定してレポートしてください。
2. 健康に関する相談、トレーニングのアドバイスなどに的確に答えてください。
"""

# ---------------------------------------------------------
# 4. サイドバー（設定・ログ表示・データ同期状態）
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 J.A.R.V.I.S. Status")
    st.success("☁️ Google Drive 同期中")
    
    st.subheader("📊 記憶データ概要")
    st.write(f"- 保持している会話ログ数: {len(st.session_state.chat_history)} 件")
    st.write(f"- 食事ログ数: {len(st.session_state.nutrition_log)} 件")
    
    st.markdown("---")
    if st.button("🔄 Driveから手動リロード"):
        st.session_state.chat_history = load_json_from_drive(DRIVE_MEMORY_FILE, default_factory=list)
        st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)
        st.success("最新データをロードしました！")
        st.rerun()

    if st.button("🗑️ 画面表示をクリア"):
        st.rerun()

# ---------------------------------------------------------
# 5. メインUI：ヘッダー
# ---------------------------------------------------------
st.title("🤖 J.A.R.V.I.S. Health & Nutrition Assistant")
st.caption("Google Drive 完全同期 | Powered by Gemini Flash")

# ---------------------------------------------------------
# 6. 入力エリア（画像アップロード ＆ チャット入力）
# ---------------------------------------------------------
col1, col2 = st.columns([1, 4])

with col1:
    uploaded_image = st.file_uploader("📷 食事写真", type=["jpg", "jpeg", "png"])

# チャット入力
user_input = st.chat_input("マスター、何かお手伝いできることはありますか？")

# ---------------------------------------------------------
# 7. メッセージ送信時の処理
# ---------------------------------------------------------
if user_input or uploaded_image:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    display_text = user_input if user_input else "【食事画像を送信しました】"
    
    st.session_state.chat_history.append({
        "role": "user",
        "text": display_text,
        "timestamp": now_str
    })
    
    with st.chat_message("user", avatar="👤"):
        st.caption(f"[{now_str}]")
        st.write(display_text)
        if uploaded_image:
            img = Image.open(uploaded_image)
            st.image(img, caption="送信された画像", use_column_width=True)

    # Geminiへのリクエスト構築
    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. が解析中..."):
            try:
                # コンテンツリストの作成
                contents = []
                
                # 直近の過去会話コンテキスト（記憶）を追加
                for msg in st.session_state.chat_history[-5:]:
                    contents.append(f"{msg['role']}: {msg['text']}")
                
                # 画像があれば追加
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    contents.append(img)
                    contents.append("この食事画像を分析し、推定カロリーと栄養素（たんぱく質、脂質、炭水化物など）を分かりやすくレポートしてください。")
                
                if user_input:
                    contents.append(f"user: {user_input}")

                # SDK（google-genai）での呼び出し
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT
                    )
                )
                
                response_text = response.text
                
                st.caption(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                st.write(response_text)
                
                # AIの応答をログに追加
                st.session_state.chat_history.append({
                    "role": "model",
                    "text": response_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # 食事画像があった場合は栄養ログにも追加
                if uploaded_image:
                    st.session_state.nutrition_log.append({
                        "timestamp": now_str,
                        "analysis": response_text
                    })
                    save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)

                # Google Drive に会話ログ（記憶）を保存
                save_json_to_drive(DRIVE_MEMORY_FILE, st.session_state.chat_history)

            except Exception as e:
                st.error(f"申し訳ありません、マスター。エラーが発生いたしました: {e}")
