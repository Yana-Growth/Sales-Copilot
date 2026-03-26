import streamlit as st
import os
import pypdf
import pandas as pd
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
def load_all_files():
    kb_texts = {}
    
    # Ищем файлы (PDF, CSV, XLSX, TXT) локально
    supported_files = []
    for root, dirs, files in os.walk("."):
        if ".git" in root or "venv" in root or ".next" in root or "node_modules" in root:
            continue
        for file in files:
            if file.lower().endswith((".pdf", ".csv", ".xlsx", ".txt")):
                supported_files.append(os.path.join(root, file))
                
    for file_path in supported_files:
        filename = os.path.basename(file_path)
        clean_name = re.sub(r'[^a-zA-Z0-9а-яА-Я._-]', '_', filename)
        
        try:
            text = ""
            if filename.lower().endswith(".pdf"):
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            elif filename.lower().endswith(".csv"):
                try:
                    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
                except Exception:
                    df = pd.read_csv(file_path, sep=';', encoding='cp1251')
                text = df.to_string(index=False)
            elif filename.lower().endswith(".xlsx"):
                df = pd.read_excel(file_path)
                text = df.to_string(index=False)
            elif filename.lower().endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                
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
    st.caption("Приложение автоматически находит все PDF, Excel (xlsx) и CSV файлы в папке репозитория (включая таблицу конкурентов).")
    
    kb_texts = load_all_files()
    
    if not kb_texts:
        st.warning("Файлы базы знаний не найдены. Как только вы загрузите их на GitHub, они появятся здесь.")
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
                    - НИКАКИХ извинений в начале. Используй consultative selling (спроси один точный вопрос в конце).
                    - РАБОТА С КОНКУРЕНТАМИ: Если клиент называет конкурента (например, Concur, TravelPerk, Navan, Amex GBT), ТЫ ОБЯЗАН найти этого конкурента в таблице из Базы Знаний. Используй СТРОГО те слабые стороны конкурента и те сильные стороны Tumodo, которые прописаны в этой таблице! Например, если лид использует Concur, обязательно упомяни их долгий онбординг, clunky UI и license fees, противопоставив им мгновенное внедрение Tumodo (zero setup cost) и удобный консьюмерский интерфейс. НЕ выдумывай общие аргументы, бери их строго из таблицы конкурентов.
                    - ПРАВИЛО ОТКАЗОВ: Если лид ЖЕСТКО отказывает (пишет "Не интересно", "Нет бюджетов", "Отстаньте"), НЕ ПЫТАЙСЯ ЕМУ ПРОДАВАТЬ. Выдай 3 варианта ОЧЕНЬ КОРОТКОГО (1-2 предложения) вежливого ответа: поблагодари за уделенное время, пожелай отличной недели и оставь микро-зацепку на будущее (например: "Всегда на связи, если решите автоматизировать тревел").
                    
                    БАЗА ЗНАНИЙ (СТРОГО ОПИРАЙСЯ НА ТАБЛИЦУ КОНКУРЕНТОВ ПРИ ОТВЕТАХ ПРО НИХ):
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
