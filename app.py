import streamlit as st
import os
import PyPDF2
import docx
import pandas as pd
from openai import OpenAI
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

# --- Боковая панель: Настройки и Загрузка Базы Знаний ---
with st.sidebar:
    st.markdown("## ⚙️ Настройки AI")
    api_key = st.text_input("OpenAI API Key (sk-...)", type="password", help="Введите ваш ключ для генерации ответов.")
    
    st.markdown("---")
    st.markdown("## 📚 База Знаний (Обучение ИИ)")
    st.markdown("Загрузите файлы Tumodo (PDF, Word, Excel), чтобы ИИ выучил ваш Tone of Voice, скрипты и данные конкурентов.")
    
    uploaded_files = st.file_uploader(
        "Загрузите брендбук, скрипты аутрича и т.д.", 
        type=['pdf', 'docx', 'xlsx', 'txt'],
        accept_multiple_files=True
    )

# --- Извлечение текста из файлов (Локальное временное обучение) ---
@st.cache_data
def extract_text_from_files(files):
    knowledge_base = ""
    if not files:
        return knowledge_base
        
    for file in files:
        try:
            if file.name.endswith('.pdf'):
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    knowledge_base += page.extract_text() + "\n"
            elif file.name.endswith('.docx'):
                doc = docx.Document(file)
                for para in doc.paragraphs:
                    knowledge_base += para.text + "\n"
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
                knowledge_base += df.to_string() + "\n"
            elif file.name.endswith('.txt'):
                knowledge_base += file.getvalue().decode("utf-8") + "\n"
        except Exception as e:
            st.sidebar.error(f"Ошибка при чтении {file.name}: {e}")
            
    return knowledge_base

kb_text = extract_text_from_files(uploaded_files)

if uploaded_files:
    st.sidebar.success(f"✅ База знаний загружена! ({len(uploaded_files)} файлов)")

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
            st.error("Пожалуйста, введите OpenAI API Key в настройках слева.")
        elif not lead_message:
            st.warning("Вставьте сообщение от лида для генерации ответа.")
        else:
            with st.spinner("Анализирую базу знаний и пишу ответ..."):
                try:
                    client = OpenAI(api_key=api_key)
                    
                    system_prompt = f"""You are a Senior Enterprise Sales Executive at Tumodo (B2B business travel platform).
Your goal is to qualify the Lead and get them on a demo call.
Tone: Confident, empathetic, speaks in numbers/ROI, business casual. 
NO apologies. Do NOT use words like 'unique', 'innovative'. Ask maximum 1 question per message.

Here is the Tumodo Knowledge Base (Use arguments from here against B2C tools or competitors if applicable):
---
{kb_text[:15000] if kb_text else "Tumodo saves up to 35% on travel spend and automates reporting. Manual tools are a bottleneck for Finance."}
---

Format output strictly as a JSON object: {{"responses": [{{"style": "...", "text": "..."}}]}}
Generate exactly TWO options: one softer (Consultative), one more direct (ROI-focused).
"""

                    user_prompt = f"""Lead Info: Role: {role}, Size: {company_size}, Region: {region}.
Lead's Message: "{lead_message}".
"""

                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={ "type": "json_object" },
                        temperature=0.7
                    )
                    
                    result = json.loads(response.choices[0].message.content)
                    
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
