import streamlit as st
import json
import os
from PIL import Image
from google import genai
from google.genai import types

# 別ファイルで作成したGoogle Drive操作用モジュールをインポート
import drive_utils

# --- ページ基本設定 ---
st.set_page_config(page_title="J.A.R.V.I.S.", page_icon="🤖", layout="wide")
st.title("🤖 J.A.R.V.I.S. - Personal Assistant")

# --- APIクライアントの初期化 ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- セッション状態の初期化 ---
if "messages" not in st.session_state:
    # Google Driveから過去の対話ログを取得（存在しない場合は空リスト）
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
    # サイドバーにプレビューを表示して確認できるようにする
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
            # Streamlitで受け取ったファイルをGemini APIのFiles APIへアップロード
            pdf_file_ref = client.files.upload(
                file=uploaded_pdf,
                config=types.UploadFileConfig(mime_type="application/pdf")
            )
        st.success(f"📎 読み込み完了:\n{uploaded_pdf.name}")


# ==========================================
# 💬 メイン対話画面（直近1往復表示）
# ==========================================
if len(st.session_state.messages) >= 2:
    # 直近のユーザー発言とAI回答を表示
    last_user_msg = st.session_state.messages[-2]
    last_ai_msg = st.session_state.messages[-1]
    
    st.chat_message(last_user_msg["role"]).write(last_user_msg["content"])
    st.chat_message(last_ai_msg["role"]).write(last_ai_msg["content"])

# --- チャット入力エリア ---
user_input = st.chat_input("メッセージを入力（例：この写真のカロリーを教えて / PDFを要約して）")

if user_input:
    # 1. ユーザーの入力を画面に即座に表示
    st.chat_message("user").write(user_input)
    
    # 2. プロンプト（Geminiに渡すコンテンツ）の構築
    contents = []
    
    # 過去の会話文脈を追加（過去ログがある場合）
    for msg in st.session_state.messages:
        contents.append(f"{msg['role']}: {msg['content']}")
    
    # サイドバーで添付された画像をプロンプトに追加
    if image_input:
        contents.append(image_input)

    # サイドバーで添付されたPDFをプロンプトに追加
    if pdf_file_ref:
        contents.append(pdf_file_ref)
        
    # 今回の最新テキスト発言を追加
    contents.append(f"user: {user_input}")

    # 3. AIの応答生成（「考え中...」スピナー表示）
    with st.chat_message("assistant"):
        with st.spinner("J.A.R.V.I.S. 分析中..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )
            ai_response_text = response.text
            st.write(ai_response_text)

    # 4. 会話履歴の更新とGoogle Driveへの保存（上書き処理）
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
    
    # Driveへ保存（既存ファイルを上書き更新）
    drive_utils.save_logs_to_drive(st.session_state.messages)
    
    # 画面の再描画（直近1往復表示を維持するため）
    st.rerun()
