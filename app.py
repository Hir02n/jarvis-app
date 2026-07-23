import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import json
from datetime import datetime
from drive_utils import load_json_from_drive, save_json_to_drive

# ---------------------------------------------------------
# 1. ページ基本設定 & Gemini API 初期化
# ---------------------------------------------------------
st.set_page_config(
    page_title="J.A.R.V.I.S. Health System",
    page_icon="🤖",
    layout="wide"
)

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"APIキーの設定エラー: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. Google Drive からデータの初期ロード
# ---------------------------------------------------------
DRIVE_MEMORY_FILE = "jarvis_memory.json"
DRIVE_NUTRITION_FILE = "nutrition_log.json"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_json_from_drive(DRIVE_MEMORY_FILE, default_factory=list)

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
# 4. サイドバー
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
st.caption("Google Drive 完全同期 | Powered by Gemini")

# ---------------------------------------------------------
# 6. 入力エリア
# ---------------------------------------------------------
col1, col2 = st.columns([1, 4])

with col1:
    uploaded_image = st.file_uploader("📷 食事写真", type=["jpg", "jpeg", "png"])

user_input = st.chat_input("マスター、何かお手伝いできることはありますか？")

# ---------------------------------------------------------
# 7. メッセージ送信時の処理（Interactions / 最新モデル呼び出し）
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

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. が解析中..."):
            try:
                contents = []
                
                # 直近の会話コンテキストを追加
                for msg in st.session_state.chat_history[-5:]:
                    contents.append(f"{msg['role']}: {msg['text']}")
                
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    contents.append(img)
                    contents.append("この食事画像を分析し、推定カロリーと栄養素（たんぱく質、脂質、炭水化物など）を分かりやすくレポートしてください。")
                
                if user_input:
                    contents.append(f"user: {user_input}")

                # Interactions API を優先的に呼び出し
                try:
                    response = client.interactions.create(
                        model="gemini-2.5-flash",
                        input=contents,
                        system_instruction=SYSTEM_PROMPT
                    )
                    # Interactions API のレスポンス解析
                    if hasattr(response, 'outputs') and response.outputs:
                        response_text = response.outputs[0].text
                    elif hasattr(response, 'text'):
                        response_text = response.text
                    else:
                        response_text = str(response)
                except Exception:
                    # フォールバック呼び出し
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        )
                    )
                    response_text = response.text
                
                st.caption(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                st.write(response_text)
                
                st.session_state.chat_history.append({
                    "role": "model",
                    "text": response_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                
                if uploaded_image:
                    st.session_state.nutrition_log.append({
                        "timestamp": now_str,
                        "analysis": response_text
                    })
                    save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)

                save_json_to_drive(DRIVE_MEMORY_FILE, st.session_state.chat_history)

            except Exception as e:
                st.error(f"申し訳ありません、マスター。エラーが発生いたしました: {e}")
