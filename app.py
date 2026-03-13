import streamlit as st
import os
import google.generativeai as genai
import json

# --- Настройка страницы ---
st.set_page_config(page_title="Tumodo Sales Copilot", page_icon="🚀", layout="wide")

# --- Стилизация под Tumodo ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
    }
    .main-header {
        color: #0F172A;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    div[data-testid="stSidebar"] {
        background-color: #1E293B;
        color: white;
    }
    .stButton>button {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        border-color: #1D4ED8;
    }
    .response-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Боковая панель: Настройки ---
with st.sidebar:
    st.markdown("## ⚙️ Настройки AI")
    api_key = st.text_input("Gemini API Key", type="password", help="Получить ключ: https://aistudio.google.com/app/apikey")
    
    selected_model_name = st.selectbox(
        "Версия модели Gemini", 
        [
            "gemini-3.1-pro",
            "gemini-3.0-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ],
        index=0
    )
    
    st.markdown("---")
    st.markdown("## 📚 База Знаний (Обучение ИИ)")
    st.markdown("ИИ автоматически использует правила, скрипты и Tone of Voice из файла `knowledge.txt`.")
    
    try:
        with open("knowledge.txt", "r", encoding="utf-8") as f:
            kb_text = f.read()
        st.success("✅ Локальная база знаний успешно подключена!")
        with st.expander("Посмотреть текущую базу знаний"):
            st.text(kb_text)
    except FileNotFoundError:
        kb_text = "Tumodo saves up to 35% on travel spend and automates reporting. Manual tools are a bottleneck for Finance."
        st.warning("⚠️ Файл knowledge.txt не найден. Используются базовые настройки.")

# --- Основной интерфейс ---
st.markdown('<p class="main-header">🚀 Tumodo Sales Copilot</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Умный AI-ассистент для идеальных ответов лидам на основе брендбука.</p>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.5], gap="large")

with col1:
    st.markdown("### 👤 Данные о Лиде")
    role = st.text_input("Должность (например: CFO, HR, CEO)", placeholder="CFO")
    company_size = st.selectbox("Размер компании", ["1-50", "51-200", "201-500", "500+"])
    region = st.selectbox("Регион/ГЕО", ["Global", "India", "UAE", "KSA", "Kazakhstan", "Germany"])
    
    st.markdown("### ✉️ Сообщение Лида")
    lead_message = st.text_area("Вставьте то, что ответил лид в LinkedIn или на почту:", height=200, placeholder="We are currently using Make My Trip and doing fine...")
    
    generate_btn = st.button("✨ Сгенерировать ответы")

with col2:
    st.markdown("### 📝 Варианты ответов")
    
    if generate_btn:
        if not api_key:
            st.error("Пожалуйста, введите Gemini API Key в настройках слева.")
        elif not lead_message:
            st.warning("Вставьте сообщение от лида для генерации ответа.")
        else:
            with st.spinner("Анализирую базу знаний и пишу ответ..."):
                try:
                    genai.configure(api_key=api_key)
                    
                    model_id = selected_model_name
                    # Для Gemini API названия 3.0 и 3.1 пишутся с дефисом, заменяем точку на дефис
                    model_id = model_id.replace(".", "-")
                    
                    model = genai.GenerativeModel(model_id)
                    
                    system_prompt = f"""You are a Senior Enterprise Sales Executive at Tumodo (B2B business travel platform).
Your goal is to qualify the Lead and get them on a demo call.
Tone: Confident, empathetic, speaks in numbers/ROI, business casual. 
NO apologies. Do NOT use words like 'unique', 'innovative'. Ask maximum 1 question per message.

Here is the Tumodo Knowledge Base (Use arguments from here against B2C tools or competitors if applicable):
---
{kb_text[:15000] if kb_text else "Tumodo saves up to 35% on travel spend and automates reporting. Manual tools are a bottleneck for Finance."}
---

Format output strictly as a JSON object with this exact structure, do NOT include markdown blocks: {{"responses": [{{"style": "Consultative", "text": "..."}}, {{"style": "Direct", "text": "..."}}]}}
Generate exactly TWO options: one softer (Consultative), one more direct (ROI-focused).
"""

                    user_prompt = f"""Lead Info: Role: {role}, Size: {company_size}, Region: {region}.
Lead's Message: "{lead_message}".
"""
                    
                    # В Gemini system prompt передается либо в настройках модели, либо просто в начале текста
                    full_prompt = system_prompt + "\n\n" + user_prompt

                    response = model.generate_content(
                        full_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.7,
                            response_mime_type="application/json",
                        )
                    )
                    
                    result = json.loads(response.text)
                    
                    for r in result.get('responses', []):
                        st.markdown(f"""
                        <div class="response-card">
                            <span style="background:#E2E8F0; color:#475569; padding:4px 8px; border-radius:4px; font-size:12px; font-weight:bold; text-transform:uppercase;">
                                {r.get('style', 'Style')}
                            </span>
                            <p style="margin-top:12px; color:#1E293B; font-size:15px; line-height:1.6;">{r.get('text', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Произошла ошибка при генерации: {str(e)}")
    else:
        st.info("Заполните данные слева и нажмите 'Сгенерировать отвеы', чтобы увидеть магию AI.")
