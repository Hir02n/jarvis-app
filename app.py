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
# 2. Google Drive からジャンル別データのロード
# ---------------------------------------------------------
DRIVE_CHAT_FILE = "chat_memory.json"
DRIVE_NUTRITION_FILE = "nutrition_log.json"
DRIVE_WORKOUT_FILE = "workout_log.json"

if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = load_json_from_drive(DRIVE_CHAT_FILE, default_factory=list)

if "nutrition_log" not in st.session_state:
    st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)

if "workout_log" not in st.session_state:
    st.session_state.workout_log = load_json_from_drive(DRIVE_WORKOUT_FILE, default_factory=list)

# 画面表示用のログ（最新の会話）
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
    
    st.subheader("📊 ジャンル別データ蓄積数")
    st.write(f"- 💬 会話記憶: **{len(st.session_state.chat_memory)} 件**")
    st.write(f"- 🥗 栄養ログ: **{len(st.session_state.nutrition_log)} 件**")
    st.write(f"- 🏋️ 運動ログ: **{len(st.session_state.workout_log)} 件**")
    
    st.markdown("---")
    if st.button("🗑️ 画面表示をクリア（記憶は保持）"):
        st.session_state.display_history = []
        st.rerun()

# ---------------------------------------------------------
# 5. メインUI
# ---------------------------------------------------------
st.title("🤖 J.A.R.V.I.S. Health & Nutrition Assistant")
st.caption("ジャンル別最適化コンテキスト | 高速＆省トークン設計")

# ---------------------------------------------------------
# 6. 会話履歴の表示（画面には最新のやり取りを表示）
# ---------------------------------------------------------
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
    
    # 💡【UI改善】送信直後に画面に自分の発言を表示！
    with st.chat_message("user", avatar="👤"):
        st.caption(f"[{now_str}]")
        st.write(display_text)
        if uploaded_image:
            img = Image.open(uploaded_image)
            st.image(img, caption="送信された画像", use_column_width=True)

    # 💡【UI改善】AIが考えているアニメーションを表示！
    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. がデータ照合中..."):
            try:
                # -----------------------------------------------------
                # 🚀 ジャンル判定と関連ログの選択（トークン削減ロジック）
                # -----------------------------------------------------
                selected_context = []
                category = "general"

                # キーワード判定による参照ログの絞り込み
                input_check = display_text.lower()
                if uploaded_image or any(k in input_check for k in ["カロリー", "食事", "食べた", "栄養", "朝食", "昼食", "夕食", "PFC"]):
                    category = "nutrition"
                    # 過去の栄養ログから最新5件のみ参照
                    selected_context = st.session_state.nutrition_log[-5:]
                elif any(k in input_check for k in ["運動", "筋トレ", "体重", "ランニング", "ジム", "ワークアウト"]):
                    category = "workout"
                    # 過去の運動ログから最新5件のみ参照
                    selected_context = st.session_state.workout_log[-5:]
                else:
                    # 通常会話は直近の会話履歴5件のみ参照
                    selected_context = st.session_state.chat_memory[-5:]

                # 参照コンテキストの構築
                context_prompt = f"【カテゴリ: {category}】関連する過去ログ:\n"
                for log_item in selected_context:
                    context_prompt += f"- {log_item}\n"
                context_prompt += f"\n上記を参考に、マスターの入力に対応してください:\n{display_text}"

                # API呼び出し
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    system_instruction=SYSTEM_PROMPT
                )
                
                contents = []
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    contents.append(img)
                    contents.append("この食事画像を分析し、推定カロリーと主要栄養素をレポートしてください。")
                
                contents.append(context_prompt)

                response = model.generate_content(contents)
                response_text = response.text
                
                # 画面上にAIの回答を表示
                st.caption(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                st.write(response_text)
                
                ai_msg = {
                    "role": "model",
                    "text": response_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # -----------------------------------------------------
                # 💾 ジャンル別にGoogle Driveへ追記保存
                # -----------------------------------------------------
                if category == "nutrition" or uploaded_image:
                    st.session_state.nutrition_log.append({"time": now_str, "user": display_text, "ai": response_text})
                    save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)
                elif category == "workout":
                    st.session_state.workout_log.append({"time": now_str, "user": display_text, "ai": response_text})
                    save_json_to_drive(DRIVE_WORKOUT_FILE, st.session_state.workout_log)
                else:
                    st.session_state.chat_memory.append(user_msg)
                    st.session_state.chat_memory.append(ai_msg)
                    save_json_to_drive(DRIVE_CHAT_FILE, st.session_state.chat_memory)

                # 画面描画用リストを最新メッセージに更新
                st.session_state.display_history = [user_msg, ai_msg]

            except Exception as e:
                st.error(f"申し訳ありません、マスター。エラーが発生いたしました: {e}")
