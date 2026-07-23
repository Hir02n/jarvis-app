import streamlit as st
import json
import os
from PIL import Image
import google.generativeai as genai  # 👈 ここを変更

# 別ファイルで作成したGoogle Drive操作用モジュールをインポート
import drive_utils

# --- ページ基本設定 ---
st.set_page_config(page_title="J.A.R.V.I.S.", page_icon="🤖", layout="wide")
st.title("🤖 J.A.R.V.I.S. - Personal Assistant")

# --- API設定 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"]) # 👈 ここを変更
model = genai.GenerativeModel("gemini-1.5-flash")     # 👈 モデル指定

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = drive_utils.load_logs_from_drive()

# ==========================================
# 👈 サイドバー（status / ファイル管理エリア）
# ==========================================
st.sidebar.header("⚙️ システム・ファイル入力")

# 1. 食事写真のアップロード
uploaded_image = st.sidebar.file_uploader(
    "📸 食事写真をアップロード", 
    type=["jpg", "jpeg", "png"]
)

image_input = None
if uploaded_image is not None:
    image_input = Image.open(uploaded_image)
    st.sidebar.image(image_input, caption="添付された食事写真", use_container_width=True)

st.sidebar.markdown("---")

# 2. PDFファイルのアップロード
uploaded_pdf = st.sidebar.file_uploader(
    "📄 PDFファイルを読み込ませる", 
    type=["pdf"]
)

pdf_file_ref = None
if uploaded_pdf is not None:
    with st.sidebar:
        with st.spinner("PDFを解析準備中..."):
            # 従来SDKでのファイルアップロード処理 👈 ここを変更
            pdf_file_ref = genai.upload_file(
                uploaded_pdf, 
                mime_type="application/pdf"
            )
        st.success(f"📎 読み込み完了:\n{uploaded_pdf.name}")


# ==========================================
# 💬 メイン対話画面（直近1往復表示）
# ==========================================
if len(st.session_state.messages) >= 2:
    last_user_msg = st.session_state.messages[-2]
    last_ai_msg = st.session_state.messages[-1]
    
    st.chat_message(last_user_msg["role"]).write(last_user_msg["content"])
    st.chat_message(last_ai_msg["role"]).write(last_ai_msg["content"])

# --- チャット入力エリア ---
user_input = st.chat_input("メッセージを入力（例：この写真のカロリーを教えて / PDFを要約して）")

if user_input:
    # 1. ユーザーの入力を表示
    st.chat_message("user").write(user_input)
    
    # 2. プロンプト（Geminiに渡す要素）の構築
    contents = []
    
    # 過去の会話文脈
    for msg in st.session_state.messages:
        contents.append(f"{msg['role']}: {msg['content']}")
    
    # 添付画像
    if image_input:
        contents.append(image_input)

    # 添付PDF
    if pdf_file_ref:
        contents.append(pdf_file_ref)
        
    # 最新の入力
    contents.append(f"user: {user_input}")

    # 3. AIの応答生成
    with st.chat_message("assistant"):
        with st.spinner("J.A.R.V.I.S. 分析中..."):
            response = model.generate_content(contents) # 👈 ここを変更
            ai_response_text = response.text
            st.write(ai_response_text)

    # 4. 会話履歴の更新と保存
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
    
    drive_utils.save_logs_to_drive(st.session_state.messages)
    
    st.rerun()
