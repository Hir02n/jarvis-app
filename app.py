import streamlit as st
import google.generativeai as genai

st.title("🤖 J.A.R.V.I.S. API Diagnostics")

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("### 🔍 利用可能なモデル一覧")
    models = genai.list_models()
    
    available_models = []
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
            
    if available_models:
        st.success("API接続成功！利用可能なモデルが見つかりました:")
        st.json(available_models)
    else:
        st.warning("API接続はできましたが、利用可能なモデルが0件です。")
        
except Exception as e:
    st.error(f"診断エラーが発生しました: {e}")
