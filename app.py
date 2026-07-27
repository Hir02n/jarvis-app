import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
from drive_utils import load_json_from_drive, save_json_to_drive

# PDFテキスト抽出用（インストールされている場合に使用）
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# ---------------------------------------------------------
# 1. ページ基本設定 & Gemini API 初期化
# ---------------------------------------------------------
st.set_page_config(
    page_title="J.A.R.V.I.S. Multi-System",
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
# 2. カテゴリ・システムプロンプト・ファイル名の定義
# ---------------------------------------------------------
CATEGORIES = {
    "🏥 健康・栄養管理": {
        "file": "jarvis_memory_health.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の健康・食事・栄養管理および生活サポートをプロフェッショナルかつスマートに行ってください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
- ユーモアを交えつつも、食事のカロリーや栄養素、健康に関するアドバイスは的確に提示してください。
"""
    },
    "⚡ ポケモン": {
        "file": "jarvis_memory_pokemon.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」であり、同時に全ポケモンのデータ・対戦環境・育成論・最新情報に精通した知能データベースです。

【役割・知識】
- ポケモンの種族値、タイプ相性、技構成、特性、持ち物、対戦考察（パーティ構築や対戦環境）についての高度な分析を提供します。
- 育成論や努力値振り、初心者向けの解説、図鑑情報まで、あらゆる質問に的確に回答してください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 「ポケモンのデータ分析でございますね、マスター」といった、J.A.R.V.I.S.らしい知的で洗練された執事のトーンを維持してください。
"""
    },
    "💬 一般・フリートーク": {
        "file": "jarvis_memory_general.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスターの日常の疑問解決、雑談、スケジュール整理、思考のブレインストーミング等をスマートにサポートしてください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
"""
    }
}

DRIVE_NUTRITION_FILE = "nutrition_log.json"

# ---------------------------------------------------------
# 3. サイドバー（カテゴリ選択・Status & ファイル入力）
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 J.A.R.V.I.S. Status")
    st.success("☁️ Google Drive 完全同期中")
    
    st.subheader("📂 カテゴリ（モード）選択")
    selected_category_name = st.radio(
        "モードを切り替えてください",
        list(CATEGORIES.keys())
    )
    
    current_category = CATEGORIES[selected_category_name]
    current_memory_file = current_category["file"]
    current_system_prompt = current_category["prompt"]

    st.markdown("---")
    
    # 選択カテゴリの記憶をDriveから取得・保持するキー
    history_key = f"full_history_{current_memory_file}"
    if history_key not in st.session_state:
        st.session_state[history_key] = load_json_from_drive(current_memory_file, default_factory=list)
        
    if "nutrition_log" not in st.session_state:
        st.session_state.nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)

    if "display_history" not in st.session_state:
        st.session_state.display_history = []

    st.subheader("📊 蓄積データ（記憶）")
    st.write(f"- モード: **{selected_category_name}**")
    st.write(f"- 会話記憶: **{len(st.session_state[history_key])} 件**")
    if selected_category_name == "🏥 健康・栄養管理":
        st.write(f"- 食事ログ: **{len(st.session_state.nutrition_log)} 件**")
    
    st.markdown("---")
    st.subheader("📎 ファイル入力")
    
    # 1. 画像アップローダー
    uploaded_image = st.file_uploader("📷 画像（食事・その他）", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        img_preview = Image.open(uploaded_image)
        st.image(img_preview, caption="添付画像", use_container_width=True)
        
    # 2. PDF資料アップローダー
    uploaded_pdf = st.file_uploader("📄 PDF資料", type=["pdf"])
    pdf_text = ""
    if uploaded_pdf:
        st.caption(f"📎 添付済み: {uploaded_pdf.name}")
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
# 4. メインUI
# ---------------------------------------------------------
st.title(f"🤖 J.A.R.V.I.S. - {selected_category_name}")
st.caption(f"記憶はDriveの「{current_memory_file}」へ同期保存されます")

# ---------------------------------------------------------
# 5. 画面表示（直近のメッセージのみ出力）
# ---------------------------------------------------------
for msg in st.session_state.display_history:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.caption(f"[{msg.get('timestamp', '')}]")
        st.write(msg["text"])

# ---------------------------------------------------------
# 6. 入力エリア
# ---------------------------------------------------------
user_input = st.chat_input(f"マスター、{selected_category_name}に関して何かお手伝いすることはありますか？")

# ---------------------------------------------------------
# 7. メッセージ送信処理（ループ防止ガード付き）
# ---------------------------------------------------------
if "last_processed_pdf" not in st.session_state:
    st.session_state.last_processed_pdf = None

if "last_processed_img" not in st.session_state:
    st.session_state.last_processed_img = None

current_pdf_name = uploaded_pdf.name if uploaded_pdf else None
current_img_name = uploaded_image.name if uploaded_image else None

has_new_user_input = bool(user_input)
has_new_pdf = uploaded_pdf and (current_pdf_name != st.session_state.last_processed_pdf)
has_new_img = uploaded_image and (current_img_name != st.session_state.last_processed_img)

if has_new_user_input or has_new_pdf or has_new_img:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if uploaded_pdf:
        st.session_state.last_processed_pdf = current_pdf_name
    if uploaded_image:
        st.session_state.last_processed_img = current_img_name

    if user_input:
        display_text = user_input
    elif uploaded_image and uploaded_pdf:
        display_text = "【画像とPDF資料を送信しました】"
    elif uploaded_image:
        display_text = "【画像を送信しました】"
    else:
        display_text = "【PDF資料を送信しました】"
    
    user_msg = {
        "role": "user",
        "text": display_text,
        "timestamp": now_str
    }
    
    # 選択中カテゴリの記憶リストに追加
    st.session_state[history_key].append(user_msg)

    with st.chat_message("user", avatar="👤"):
        st.caption(f"[{now_str}]")
        st.write(display_text)

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. が思考中..."):
            try:
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    system_instruction=current_system_prompt
                )
                
                context_prompt = f"以下はこれまでの「{selected_category_name}」に関する過去の記憶です:\n"
                for h in st.session_state[history_key][:-1]:
                    context_prompt += f"- {h['role']}: {h['text']}\n"
                
                context_prompt += f"\n上記の記憶・資料を踏まえて、最新の入力に対応してください:\n{display_text}"

                contents = []
                
                # 画像の追加
                if uploaded_image:
                    img = Image.open(uploaded_image)
                    contents.append(img)
                    if not user_input and not uploaded_pdf:
                        if selected_category_name == "🏥 健康・栄養管理":
                            context_prompt += "\nこの食事画像を分析し、推定カロリーと栄養素をレポートしてください。"
                        else:
                            context_prompt += "\nこの画像を分析してください。"

                # PDFの追加（バイト列として直接伝達）
                if uploaded_pdf:
                    pdf_data = {
                        "mime_type": "application/pdf",
                        "data": uploaded_pdf.getvalue()
                    }
                    contents.append(pdf_data)
                    if not user_input and not uploaded_image:
                        context_prompt += "\nこのPDF資料の内容を読み取り、要約や構成案を作成してください。"

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
                
                st.session_state[history_key].append(ai_msg)
                st.session_state.display_history = [user_msg, ai_msg]
                
                # 健康管理モードかつ画像添付時のみ食事ログとして別途保存
                if selected_category_name == "🏥 健康・栄養管理" and uploaded_image:
                    st.session_state.nutrition_log.append({
                        "timestamp": now_str,
                        "analysis": response_text
                    })
                    save_json_to_drive(DRIVE_NUTRITION_FILE, st.session_state.nutrition_log)

                # 現在のカテゴリ用JSONファイルに会話ログを保存
                save_json_to_drive(current_memory_file, st.session_state[history_key])

                st.rerun()

            except Exception as e:
                st.error(f"エラーが発生いたしました: {e}")
