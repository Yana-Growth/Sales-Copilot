import streamlit as st
import os
import pypdf
import google.generativeai as genai
import re

st.set_page_config(page_title="Tumodo Sales Copilot", layout="wide", page_icon="💼")

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #1E293B; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stTextInput input, .stTextArea textarea, .stSelectbox select { border-radius: 8px !important; }
    .stButton > button { background-color: #2563EB !important; color: white !important; border-radius: 8px !important; font-weight: 600 !important; border: none !important; }
    .kb-status { padding: 10px; border-radius: 8px; background-color: #0F172A; margin-bottom: 8px; display: flex; justify-content: space-between; font-size: 14px; word-break: break-all;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_all_pdfs():
    kb_texts = {}
    
    # Ищем PDF файлы локально
    pdf_files = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "venv" in root or ".next" in root or "node_modules" in root:
            continue
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
                
    for file_path in pdf_files:
        filename = os.path.basename(file_path)
        # Очистка имени файла для безопасного отображения и хранения ключей
        clean_name = re.sub(r'[^a-zA-Z0-9а-яА-Я._-]', '_', filename)
        
        try:
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            kb_texts[clean_name] = text
        except Exception as e:
            kb_texts[clean_name] = None
            
    return kb_texts

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Настройки")
    api_key = st.text_input("Gemini API Key", type="password", help="Ключ из Google AI Studio")
    
    selected_model = st.selectbox(
        "Выбор модели (строго из списка AI Studio)",
        [
            "gemini-3.1-pro-preview",
            "gemini-pro-latest",
            "gemini-3-flash-preview",
            "gemini-flash-latest",
            "gemini-3.1-flash-lite-preview",
            "gemini-flash-lite-latest",
            "gemini-3.1-flash-image-preview",
            "gemini-3-pro-image-preview"
        ],
        index=0
    )
    
    st.divider()
    st.subheader("📚 База знаний")
    st.caption("Приложение автоматически находит все PDF в папке репозитория (включая папку аутрич, если она загружена на github).")
    
    kb_texts = load_all_pdfs()
    
    if not kb_texts:
        st.warning("PDF-файлы не найдены. Как только вы зальете их на GitHub рядом со скриптом, они появятся здесь.")
    else:
        for filename, text in kb_texts.items():
            status_icon = "✅" if text else "❌ (Ошибка)"
            st.markdown(f'<div class="kb-status"><span>{filename}</span> <span>{status_icon}</span></div>', unsafe_allow_html=True)
            
    if st.button("🔄 Перезагрузить базу", key="refresh_kb"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN APP ---
st.title("💼 Tumodo Sales Copilot (Stas Klyuy)")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Вводные данные")
    
    company_context = st.text_input("Контекст об оппоненте (Необязательно)", placeholder="Например: Внедряют SAP, 500+ сотрудников")
    region = st.selectbox("Регион лида", ["UAE", "Saudi Arabia (KSA)", "Индия", "Казахстан", "Германия", "Global"])
    
    lead_history = st.text_area("История переписки (включая логи GetSales):", height=350, placeholder="Вставьте скопированный текст из GetSales (включая системные сообщения об Automation Connect, теги и т.д.)")
    
    generate_btn = st.button("🚀 Сгенерировать ответы", use_container_width=True)

with col2:
    st.subheader("2. Варианты ответов")
    
    if generate_btn:
        if not api_key:
            st.error("Пожалуйста, введите Gemini API Key в настройках слева.")
        elif not lead_history:
            st.error("Пожалуйста, вставьте историю переписки.")
        else:
            with st.spinner("Анализирую логи GetSales и пишу ответ..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(selected_model)
                    
                    kb_context = ""
                    for label, text in kb_texts.items():
                        if text:
                            kb_context += f"--- {label} ---\n{text[:3000]}\n\n"
                            
                    system_prompt = f"""
                    Ты — Стас Клюев (Stanislav Klyuy), Senior Enterprise Sales Executive в компании Tumodo (B2B).
                    Мы общаемся от лица Стаса Клюева. Твоя главная цель — квалифицировать лида в LinkedIn и закрыть его на звонок/демо.
                    
                    ВВОДНЫЕ О ЛИДЕ / СДЕЛКЕ:
                    - Контекст: {company_context}
                    - Регион: {region}
                    
                    ИСТОРИЯ ПЕРЕПИСКИ:
                    {lead_history}
                    
                    ЗАДАЧА:
                    Проигнорируй весь технический шум (Pipeline Stage 10 Mar 09:32, Automation Connect, Tags added). Напиши ровно 3 варианта продолжения диалога от лица Стаса Клюева на основе последнего сообщения лида.
                    Если лид написал на английском — пиши на английском.
                    
                    ПРАВИЛА TUMODO:
                    - Будь уверенным, говори на языке бизнеса. Подписывайся как Stas Klyuy.
                    - НИКАКИХ извинений в начале. Используй consultative selling (один точный вопрос в конце).
                    - Если клиент использует Qashio, B2C сервис и т.п., мягко отрабатывай: сравнивай B2C и B2B платформу Tumodo (инвойсинг, 0 скрытых комиссий).
                    
                    БАЗА ЗНАНИЙ (учитывай эти тезисы):
                    {kb_context}
                    
                    ОБЯЗАТЕЛЬНО: Раздели 3 варианта строго строкой "====SEPARATOR====".
                    
                    Формат:
                    Вариант 1: Короткий и прямой (Direct)
                    [Текст]
                    ====SEPARATOR====
                    Вариант 2: Мягкий (Consultative)
                    [Текст]
                    ====SEPARATOR====
                    Вариант 3: Отработка решения (Competitor challenge)
                    [Текст]
                    """
                    
                    response = model.generate_content(system_prompt)
                    raw_text = response.text
                    
                    variants = [v.strip() for v in raw_text.split("====SEPARATOR====") if v.strip()]
                    
                    for i, variant in enumerate(variants):
                        st.markdown(f'<div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 16px; color: #1E293B;"><strong style="color:#2563EB;">Вариант {i+1}</strong><br><br>{variant}</div>', unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Ошибка при обращении к Gemini: {e}")
