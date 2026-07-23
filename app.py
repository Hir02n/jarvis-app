import streamlit as st
import json
import os
from PIL import Image
import google.generativeai as genai

# 別ファイルで作成したGoogle Drive操作用モジュールをインポート
import drive_utils

# --- ページ基本設定 ---
st.set_page_config(page_title="J.A.R.V.I.S.", page_icon="🤖", layout="wide")
st.title("🤖 J.A.R.V.I.S. - Personal Assistant")

# --- API設定 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# --- セッション状態の初期化（安全なログ読み込み） ---
if "messages" not in st.session_state:
    try:
        if hasattr(drive_utils, "load_logs_from_drive"):
            st.session_state.messages = drive_utils.load_logs_from_drive()
        elif hasattr(drive_utils, "load_logs"):
            st.session_state.messages = drive_utils.load_logs()
        else:
            st.session_state.messages = []
    except Exception as e:
        st.session_state.messages = []

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
    try:
        image_input = Image.open(uploaded_image)
        st.sidebar.image(image_input, caption="添付された食事写真", use_container_width=True)
    except Exception as e:
        st.sidebar.error("画像の読み込みに失敗しました。")

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
            try:
                pdf_file_ref = genai.upload_file(
                    uploaded_pdf, 
                    mime_type="application/pdf"
                )
                st.success(f"📎 読み込み完了:\n{uploaded_pdf.name}")
            except Exception as e:
                st.error(f"PDFアップロードエラー: {e}")

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
    # 1. ユーザーの入力を画面表示
    st.chat_message("user").write(user_input)
    
    # 2. プロンプト（Geminiに渡す要素）の構築
    contents = []
    
    # 過去の文脈を綺麗なテキストプロンプトとして構築
    context_text = ""
    for msg in st.session_state.messages:
        role_name = "User" if msg["role"] == "user" else "J.A.R.V.I.S."
        context_text += f"{role_name}: {msg['content']}\n"
    
    context_text += f"User: {user_input}"
    
    # テキストプロンプトを追加
    contents.append(context_text)
    
    # 添付画像があれば追加
    if image_input:
        contents.append(image_input)

    # 添付PDFがあれば追加
    if pdf_file_ref:
        contents.append(pdf_file_ref)

    # 3. AIの応答生成
    with st.chat_message("assistant"):
        with st.spinner("J.A.R.V.I.S. 分析中..."):
            try:
                response = model.generate_content(contents)
                ai_response_text = response.text
                st.write(ai_response_text)
                
                # 4. 会話履歴の更新と保存（成功時のみ）
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
                
                try:
                    if hasattr(drive_utils, "save_logs_to_drive"):
                        drive_utils.save_logs_to_drive(st.session_state.messages)
                    elif hasattr(drive_utils, "save_logs"):
                        drive_utils.save_logs(st.session_state.messages)
                except Exception as save_err:
                    st.warning(f"ログ保存時に警告が発生しました: {save_err}")
                
                st.rerun()

            except Exception as e:
                st.error(f"応答生成時にエラーが発生しました: {e}")
