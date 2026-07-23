import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
from drive_utils import load_json_from_drive, save_json_to_drive

# PDFテキスト抽出用に追加（標準で使える簡易抽出）
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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
# 2. Google Drive からデータのロード（既存の単一ファイルのみ）
# ---------------------------------------------------------
DRIVE_MEMORY_FILE = "jarvis_memory.json"
DRIVE_NUTRITION_FILE = "nutrition_log.json"

if "full_history" not in st.session_state:
    st.session_state.full_history = load_json_from_drive(DRIVE_MEMORY_FILE, default_factory=list)

if "nutrition_log" not in st.session_state:
    st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)

if "display_history" not in st.session_state:
    st.session_state.display_history = []

# ---------------------------------------------------------
# 3. システムプロンプト
# ---------------------------------------------------------
SYSTEM_PROMPT = """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の健康・栄養管理および各種サポートをプロフェッショナルかつスマートに行ってください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
- ユーモアを交えつつも、データやアドバイスは的確かつ迅速に提示してください。
"""

# ---------------------------------------------------------
# 4. サイドバー（Status ＆ ファイルアップロード）
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 J.A.R.V.I.S. Status")
    st.success("☁️ Google Drive 完全同期中")
    
    st.subheader("📊 蓄積データ（記憶）")
    st.write(f"- 保持している会話記憶: **{len(st.session_state.full_history)} 件**")
    st.write(f"- 記録した食事ログ: **{len(st.session_state.nutrition_log)} 件**")
    
    st.markdown("---")
    st.subheader("📎 ファイル入力")
    
    # 1. 食事写真
    uploaded_image = st.file_uploader("📷 食事写真", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        img_preview = Image.open(uploaded_image)
        st.image(img_preview, caption="添付された食事写真", use_container_width=True)
        
    # 2. PDF資料
    uploaded_pdf = st.file_uploader("📄 PDF資料", type=["pdf"])
    pdf_text = ""
    if uploaded_pdf:
        st.caption(f"📎 添付済み: {uploaded_pdf.name}")
        # 安全にPDFからテキストを抽出
        if PdfReader:
            try:
                reader = PdfReader(uploaded_pdf)
                for page in reader.pages:
                    pdf_text += page.extract_text() or ""
            except Exception as pdf_err:
                st.warning(f"PDFテキストの読み取りに失敗しました: {pdf_err}")
    
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
for msg in st.session_state.display_history:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.caption(f"[{msg.get('timestamp', '')}]")
        st.write(msg["text"])

# ---------------------------------------------------------
# 7. 入力エリア
# ---------------------------------------------------------
user_input = st.chat_input("マスター、何かお手伝いできることはありますか？")

# ---------------------------------------------------------
# 8. メッセージ送信処理
# ---------------------------------------------------------
if user_input or uploaded_image or uploaded_pdf:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if user_input:
        display_text = user_input
    elif uploaded_image and uploaded_pdf:
        display_text = "【画像とPDF資料を送信しました】"
    elif uploaded_image:
        display_text = "【食事画像を送信しました】"
    else:
        display_text = "【PDF資料を送信しました】"
    
    user_msg = {
        "role": "user",
        "text": display_text,
        "timestamp": now_str
    }
    
    st.session_state.full_history.append(user_msg)

    with st.chat_message("user", avatar="👤"):
        st.caption(f"[{now_str}]")
        st.write(display_text)

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. が思考中..."):
            try:
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    system_instruction=SYSTEM_PROMPT
                )
                
                context_prompt = "以下はこれまでの過去の会話の記憶です:\n"
                for h in st.session_state.full_history[:-1]:
                    context_prompt += f"- {h['role']}: {h['text']}\n"
                
                # PDFから抽出したテキストがあればプロンプトに含める
                if pdf_text:
                    context_prompt += f"\n【添付PDF資料の内容】:\n{pdf_text[:4000]}\n" # 長すぎる場合のカット保護

                context_prompt += f"\n上記の記憶・資料を踏まえて、最新の入力に対応してください:\n{display_text}"

                contents = []
                
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    contents.append(img)
                    if not user_input and not uploaded_pdf:
                        context_prompt += "\nこの食事画像を分析し、推定カロリーと栄養素をレポートしてください。"

                contents.append(context_prompt)

                response = model.generate_content(contents)
                response_text = response.text
                
                st.caption(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                st.write(response_text)
                
                ai_msg = {
                    "role": "model",
                    "text": response_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.full_history.append(ai_msg)
                st.session_state.display_history = [user_msg, ai_msg]
                
                if uploaded_image:
                    st.session_state.nutrition_log.append({
                        "timestamp": now_str,
                        "analysis": response_text
                    })
                    save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)

                save_json_to_drive(DRIVE_MEMORY_FILE, st.session_state.full_history)

                st.rerun()

            except Exception as e:
                st.error(f"エラーが発生いたしました: {e}")
