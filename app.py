import streamlit as st
import google.generativeai as genai
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
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"APIキーの設定エラー: {e}")
    st.stop()

MODEL_NAME = "gemini-flash-latest"

# ---------------------------------------------------------
# 2. Google Drive からデータのロード（記憶の保持）
# ---------------------------------------------------------
DRIVE_MEMORY_FILE = "jarvis_memory.json"
DRIVE_NUTRITION_FILE = "nutrition_log.json"

# 全データ（記憶）をロード
if "full_history" not in st.session_state:
    st.session_state.full_history = load_json_from_drive(DRIVE_MEMORY_FILE, default_factory=list)

if "nutrition_log" not in st.session_state:
    st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)

# 画面表示用ログ（最新の1往復分だけを保持するリスト）
if "display_history" not in st.session_state:
    st.session_state.display_history = []

# ---------------------------------------------------------
# 3. システムプロンプト
# ---------------------------------------------------------
SYSTEM_PROMPT = """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の健康・栄養管理をプロフェッショナルかつスマートにサポートしてください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
- ユーモアを交えつつも、データやアドバイスは的確かつ迅速に提示してください。
"""

# ---------------------------------------------------------
# 4. サイドバー（ステータス表示）
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 J.A.R.V.I.S. Status")
    st.success("☁️ Google Drive 完全同期中")
    
    st.subheader("📊 蓄積データ（記憶）")
    st.write(f"- 保持している会話記憶: **{len(st.session_state.full_history)} 件**")
    st.write(f"- 記録した食事ログ: **{len(st.session_state.nutrition_log)} 件**")
    
    st.markdown("---")
    if st.button("🗑️ 画面表示をクリア（記憶は保持）"):
        st.session_state.display_history = []
        st.rerun()

# ---------------------------------------------------------
# 5. メインUI
# ---------------------------------------------------------
st.title("🤖 J.A.R.V.I.S. Health & Nutrition Assistant")
st.caption("画面はスッキリ | 記憶はGoogle Driveへ全追記保存")

# ---------------------------------------------------------
# 6. 画面表示（直近のメッセージのみ出力）
# ---------------------------------------------------------
# 過去の全ログではなく、display_history（直近）だけを描画
for msg in st.session_state.display_history:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.caption(f"[{msg.get('timestamp', '')}]")
        st.write(msg["text"])

# ---------------------------------------------------------
# 7. 入力エリア
# ---------------------------------------------------------
col1, col2 = st.columns([1, 4])

with col1:
    uploaded_image = st.file_uploader("📷 食事写真", type=["jpg", "jpeg", "png"])

user_input = st.chat_input("マスター、何かお手伝いできることはありますか？")

# ---------------------------------------------------------
# 8. メッセージ送信処理
# ---------------------------------------------------------
if user_input or uploaded_image:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    display_text = user_input if user_input else "【食事画像を送信しました】"
    
    user_msg = {
        "role": "user",
        "text": display_text,
        "timestamp": now_str
    }
    
    # 1. 記憶（全体）と画面表示（直近）の両方に追記
    st.session_state.full_history.append(user_msg)
    st.session_state.display_history = [user_msg] # 画面表示は最新のみに更新

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT
        )
        
        # 2. 過去の全会話履歴を文脈（コンテキスト）としてGeminiに教える
        context_prompt = "以下はこれまでの過去の会話の記憶です:\n"
        for h in st.session_state.full_history[:-1]:
            context_prompt += f"- {h['role']}: {h['text']}\n"
        context_prompt += f"\n上記の記憶を踏まえて、最新の入力に対応してください:\n{display_text}"

        contents = []
        if uploaded_image:
            img = Image.open(uploaded_image)
            contents.append(img)
            contents.append("この食事画像を分析し、推定カロリーと栄養素をレポートしてください。")
        
        contents.append(context_prompt)

        with st.spinner("J.A.R.V.I.S. が思考中..."):
            response = model.generate_content(contents)
            response_text = response.text
        
        ai_msg = {
            "role": "model",
            "text": response_text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 3. 応答を記憶（全体）と画面（直近）に追記
        st.session_state.full_history.append(ai_msg)
        st.session_state.display_history.append(ai_msg)
        
        # 4. 食事ログと会話記憶を Google Drive へ追記保存（蓄積）
        if uploaded_image:
            st.session_state.nutrition_log.append({
                "timestamp": now_str,
                "analysis": response_text
            })
            save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)

        # 過去ログを含めた全履歴をDriveに保存
        save_json_to_drive(DRIVE_MEMORY_FILE, st.session_state.full_history)

        st.rerun()

    except Exception as e:
        st.error(f"エラーが発生いたしました: {e}")
