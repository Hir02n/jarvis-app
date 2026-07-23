import streamlit as st
import google.generativeai as genai
import json
import os
from drive_utils import load_memory_from_drive, save_memory_to_drive

# ----------------------------------------------------
# 1. ページ初期設定
# ----------------------------------------------------
st.set_page_config(
    page_title="J.A.R.V.I.S.",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 J.A.R.V.I.S.")

# ----------------------------------------------------
# 2. APIキーおよび設定の読み込み
# ----------------------------------------------------
# Streamlit Secrets から Gemini API キーを取得設定
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Secrets に GEMINI_API_KEY が設定されていません。")
    st.stop()

# モデルのセットアップ
model = genai.GenerativeModel("gemini-1.5-pro")

# ----------------------------------------------------
# 3. 記憶データ（会話履歴）の読み込み
# ----------------------------------------------------
# セッション状態にメッセージ履歴がなければ Drive から読み込み
if "messages" not in st.session_state:
    try:
        loaded_messages = load_memory_from_drive()
        if loaded_messages and isinstance(loaded_messages, list):
            st.session_state.messages = loaded_messages
        else:
            st.session_state.messages = []
    except Exception as e:
        st.warning(f"記憶の読み込みに失敗したため、新規セッションを開始します: {e}")
        st.session_state.messages = []

# ----------------------------------------------------
# 4. 画面表示処理（★ご要望通り「表示は0件」に設定）
# ----------------------------------------------------
# 💡 過去のメッセージ描画処理（for message in st.session_state.messages: ...）は
# あえてスキップ（コメントアウト）しているため、画面には一切表示されません。

# ----------------------------------------------------
# 5. チャット入力・処理・応答
# ----------------------------------------------------
if user_input := st.chat_input("Jarvisにメッセージを送信..."):
    
    # ユーザーの入力を画面に表示
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # メモリ（履歴）に追加
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Gemini API 用にプロンプト（過去の全履歴含む）を作成
    prompt_history = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "model"
        prompt_history.append({"role": role, "parts": [msg["content"]]})
    
    # AIの応答を生成
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                # 過去の文脈（履歴）を持たせて送信
                response = model.generate_content(prompt_history)
                bot_response = response.text
                st.markdown(bot_response)
                
                # メモリ（履歴）にAIの返答を追加
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
                # Google Drive に最新の全記憶（json）を自動保存
                save_memory_to_drive(st.session_state.messages)
                
            except Exception as e:
                st.error(f"応答の生成中にエラーが発生しました: {e}")
