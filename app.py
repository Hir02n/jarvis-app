import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from drive_utils import load_json_from_drive, save_json_to_drive

# 画面設定
st.set_page_config(page_title="J.A.R.V.I.S.", layout="wide")
st.title("🤖 J.A.R.V.I.S. Health & Nutrition Assistant")
st.caption("Google Drive 完全同期 | Powered by Gemini 2.5 Flash")

# クライアント初期化（SecretからAPIキーを取得）
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_NAME = "gemini-2.5-flash"

# システムプロンプト
SYSTEM_INSTRUCTION = """
あなたは映画『アイアンマン』に登場する超高性能AI「J.A.R.V.I.S.（ジャービス）」です。
ユーザーを「マスター」と呼び、洗練された執事のように丁寧かつ知的にサポートしてください。
"""

# 入力フォーム
uploaded_file = st.file_uploader("📷 食事写真", type=["jpg", "jpeg", "png"])
user_prompt = st.chat_input("メッセージを入力してください...")

if user_prompt:
    # ユーザー発言の描画（画面上にはこの回の入力だけを表示）
    with st.chat_message("user"):
        st.write(user_prompt)

    # 応答生成
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                contents = []
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    contents.append(img)
                contents.append(user_prompt)

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION
                    )
                )
                
                st.write(response.text)
                
                # Drive保存処理（裏側で非表示ログとして保存）
                # log_data を構成して save_json_to_drive(...) を呼ぶ処理

            except Exception as e:
                st.error(f"申し訳ありません、マスター。エラーが発生いたしました: {e}")
