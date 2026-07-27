import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
from zoneinfo import ZoneInfo  # 日本時間（JST）指定用
from drive_utils import load_json_from_drive, save_json_to_drive

# ---------------------------------------------------------
# 💡 日本時間（JST）取得用のヘルパー関数
# ---------------------------------------------------------
def get_jst_now_str():
    return datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------
# 1. ページ基本設定 & Gemini API 初期化
# ---------------------------------------------------------
st.set_page_config(
    page_title="J.A.R.V.I.S. Auto-System",
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
# 2. カテゴリ・システムプロンプトの定義
# ---------------------------------------------------------
CATEGORIES = {
    "health": {
        "name": "🏥 健康・栄養管理",
        "file": "jarvis_memory_health.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の健康・食事・栄養管理および生活サポートをプロフェッショナルかつスマートに行ってください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
- 食事のカロリーや栄養素、健康に関するアドバイスを的確に提示してください。
"""
    },
    "work": {
        "name": "💼 仕事・業務サポート",
        "file": "jarvis_memory_work.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスター（ユーザー）の最高執事兼優秀な秘書として、仕事、ビジネス文書作成、タスク整理、メール推敲、プロジェクトのアイデア出し、資料分析などをプロフェッショナルにサポートしてください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 「業務のサポートでございますね、マスター」といった、知的で極めて洗練されたビジネス執事のトーンを維持してください。
- 結論から分かりやすく、ロジカルかつ迅速に解答を作成してください。
"""
    },
    "pokemon": {
        "name": "⚡ ポケモン",
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
    "general": {
        "name": "💬 一般・フリートーク",
        "file": "jarvis_memory_general.json",
        "prompt": """
あなたは映画『アイアンマン』に登場するAIアシスタント「J.A.R.V.I.S.（ジャービス）」です。
マスターの日常の疑問解決、雑談、思考のブレインストーミング等をスマートにサポートしてください。

【口調・文体ルール】
- ユーザーを「マスター」と呼んでください。
- 丁寧、誠実、かつ洗練された執事のようなトーンで話してください。
"""
    }
}

DRIVE_NUTRITION_FILE = "nutrition_log.json"

# ---------------------------------------------------------
# 💡 自動カテゴリ判別関数
# ---------------------------------------------------------
def classify_category(text_input, has_image, has_pdf):
    if not text_input and has_image:
        return "health"
    
    classify_prompt = f"""
以下のユーザーの入力文が、どのカテゴリに最も適しているか分類してください。
回答は「health」「work」「pokemon」「general」のいずれか1単語のみで答えてください。

【分類基準】
- health: 食事、栄養、カロリー、体重、運動、睡眠、健康に関する相談
- work: 仕事、ビジネス、メール作成・推敲、タスク、会議、プレゼン、報告書、スケジュール、プログラミング、資料作成・分析
- pokemon: ポケモン、対戦、育成論、技、特性、タイプ、図鑑、ポケモンのゲーム/アニメに関する話題
- general: 上記以外の日常会話、雑談、マーベル、その他の気軽な質問

ユーザーの入力:
"{text_input}"
"""
    try:
        classifier_model = genai.GenerativeModel(MODEL_NAME)
        res = classifier_model.generate_content(classify_prompt)
        category_code = res.text.strip().lower()
        if category_code in CATEGORIES:
            return category_code
    except Exception:
        pass
    
    return "general"

# 💡 安全にDrive上のログへ「確実に追記保存」するヘルパー関数
def append_and_save_memory(filename, new_messages):
    latest_memory = load_json_from_drive(filename, default_factory=list)
    if not isinstance(latest_memory, list):
        latest_memory = []
    
    for msg in new_messages:
        latest_memory.append(msg)
        
    save_json_to_drive(filename, latest_memory)
    return latest_memory

# ---------------------------------------------------------
# 3. サイドバー
# ---------------------------------------------------------
with st.sidebar:
    st.title("🤖 J.A.R.V.I.S. Status")
    st.success("☁️ Google Drive 完全同期中")
    st.info("🧠 自動判別（健康/仕事/ポケモン/雑談）")

    if "display_history" not in st.session_state:
        st.session_state.display_history = []

    if "last_detected_category" in st.session_state:
        st.subheader("📊 直近の判定カテゴリ")
        st.write(f"直近モード: **{st.session_state.last_detected_category}**")

    st.markdown("---")
    st.subheader("📎 ファイル入力")
    
    uploaded_image = st.file_uploader("📷 画像（食事・その他）", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        img_preview = Image.open(uploaded_image)
        st.image(img_preview, caption="添付画像", use_container_width=True)
        
    uploaded_pdf = st.file_uploader("📄 PDF資料", type=["pdf"])
    if uploaded_pdf:
        st.caption(f"📎 添付済み: {uploaded_pdf.name}")
    
    st.markdown("---")
    if st.button("🗑️ 画面表示をクリア（記憶は保持）"):
        st.session_state.display_history = []
        st.rerun()

# ---------------------------------------------------------
# 4. メインUI
# ---------------------------------------------------------
st.title("🤖 J.A.R.V.I.S. Smart Assistant")
st.caption("会話内容から「健康」「仕事」「ポケモン」「フリートーク」を自動判別して個別記憶します")

# ---------------------------------------------------------
# 5. 画面表示
# ---------------------------------------------------------
for msg in st.session_state.display_history:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.caption(f"[{msg.get('timestamp', '')}]")
        st.write(msg["text"])

# ---------------------------------------------------------
# 6. 入力エリア
# ---------------------------------------------------------
user_input = st.chat_input("マスター、何かお手伝いすることはありますか？")

# ---------------------------------------------------------
# 7. メッセージ送信処理
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
    now_str = get_jst_now_str()
    
    if uploaded_pdf:
        st.session_state.last_processed_pdf = current_pdf_name
    if uploaded_image:
        st.session_state.last_processed_img = current_img_name

    display_text = user_input if user_input else ("【画像を送信しました】" if uploaded_image else "【PDF資料を送信しました】")

    with st.chat_message("user", avatar="👤"):
        st.caption(f"[{now_str}]")
        st.write(display_text)

    with st.chat_message("model", avatar="🤖"):
        with st.spinner("J.A.R.V.I.S. が思考中..."):
            try:
                # 1. カテゴリを自動判定
                cat_key = classify_category(display_text, bool(uploaded_image), bool(uploaded_pdf))
                cat_info = CATEGORIES[cat_key]
                st.session_state.last_detected_category = cat_info["name"]
                
                # 2. 最新の記憶をDriveから直接ロード
                current_history = load_json_from_drive(cat_info["file"], default_factory=list)

                user_msg = {"role": "user", "text": display_text, "timestamp": now_str}

                # 3. AIモデルの呼び出し
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    system_instruction=cat_info["prompt"]
                )
                
                context_prompt = f"以下はこれまでの「{cat_info['name']}」に関する記憶です:\n"
                for h in current_history:
                    context_prompt += f"- {h['role']}: {h['text']}\n"
                
                context_prompt += f"\n上記の記憶・資料を踏まえて、最新の入力に対応してください:\n{display_text}"

                contents = []
                if uploaded_image:
                    contents.append(Image.open(uploaded_image))
                    if cat_key == "health" and not user_input:
                        context_prompt += "\nこの食事画像を分析し、推定カロリーと栄養素をレポートしてください。"

                if uploaded_pdf:
                    contents.append({
                        "mime_type": "application/pdf",
                        "data": uploaded_pdf.getvalue()
                    })

                contents.append(context_prompt)

                response = model.generate_content(contents)
                response_text = f"【分類: {cat_info['name']}】\n\n" + response.text
                
                ai_now_str = get_jst_now_str()
                
                st.caption(f"[{ai_now_str}]")
                st.write(response_text)
                
                ai_msg = {
                    "role": "model",
                    "text": response.text,
                    "timestamp": ai_now_str
                }
                
                st.session_state.display_history = [user_msg, {"role": "model", "text": response_text, "timestamp": ai_msg["timestamp"]}]
                
                # 4. Driveへの追加保存（`jarvis_memory_work.json` 等へ保存されます）
                append_and_save_memory(cat_info["file"], [user_msg, ai_msg])

                # 健康管理の場合の栄養ログ追加保存
                if cat_key == "health" and uploaded_image:
                    nutrition_log = load_json_from_drive(DRIVE_NUTRITION_FILE, default_factory=list)
                    nutrition_log.append({"timestamp": now_str, "analysis": response.text})
                    save_json_to_drive(DRIVE_NUTRITION_FILE, nutrition_log)

                st.rerun()

            except Exception as e:
                st.error(f"エラーが発生いたしました: {e}")
