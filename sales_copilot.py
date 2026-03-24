import streamlit as st
import os
import pypdf
from openai import OpenAI
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
    api_key = st.text_input("OpenAI API Key", type="password")
    
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
            st.error("Пожалуйста, введите OpenAI API Key в настройках слева.")
        elif not lead_history:
            st.error("Пожалуйста, вставьте историю переписки.")
        else:
            with st.spinner("Анализирую логи GetSales и пишу ответ..."):
                try:
                    client = OpenAI(api_key=api_key)
                    
                    kb_context = ""
                    for label, text in kb_texts.items():
                        if text:
                            kb_context += f"--- {label} ---\n{text[:3000]}\n\n"
                            
                    system_prompt = f"""
                    Ты — Стас Клюев (Stanislav Klyuy), Senior Enterprise Sales Executive в компании Tumodo (B2B платформа управления командировками).
                    Мы общаемся от лица Стаса Клюева. Твоя главная цель — квалифицировать лида в LinkedIn и закрыть его на звонок/демо.
                    
                    ВВОДНЫЕ О ЛИДЕ / СДЕЛКЕ:
                    - Пользовательский контекст: {company_context}
                    - Регион: {region}
                    
                    ИСТОРИЯ ПЕРЕПИСКИ (СЫРЫЕ ЛОГИ GetSales):
                    Пользователь вставит сырой лог событий из системы "GetSales". Твоя задача — проигнорировать все технические элементы (обозначения времени, "Automation Connect & follow-up", "Pipeline Stage changed", "Contact data enriched", "sent LinkedIn Message"). 
                    Смотри сквозь этот шум и вычлени ТОЛЬКО суть сообщений между Стасом и клиентом.
                    Проанализируй самый последний ответ клиента и придумай, как Стасу блестяще продолжить этот диалог.
                    
                    ПРАВИЛА И TONE OF VOICE TUMODO:
                    - Будь уверенным, эмпатичным, говори на языке бизнеса и эффективности.
                    - Подписывайся как Stas Klyuy (где это органично в LinkedIn).
                    - НИКАКИХ извинений в начале сообщений.
                    - Используй consultative selling (задавай 1 точный квалифицирующий вопрос в конце).
                    - Если клиент ответил, что использует конкурента (например Qashio) или B2C-сервис, ненавязчиво покажи экспертизу в том, чем Tumodo отличается (глубокая B2B интеграция, инвойсинг, 0 скрытых комиссий) и спроси, полностью ли они довольны.
                    - Специфика регионов: Для UAE и KSA важны автоматизация, контроль бюджетов и статус.
                    
                    БАЗА ЗНАНИЙ TUMODO (Используй эти тезисы, опираясь на папку аутрич и гайды):
                    {kb_context}
                    
                    ЗАДАЧА:
                    Выдай ровно 3 варианта отличного ответа для Стаса Клюева на основе последнего сообщения лида.
                    Если лид написал на английском — пиши ответ на английском.
                    
                    Раздели варианты строго строкой "====SEPARATOR====".
                    
                    Формат вывода:
                    Вариант 1: Короткий и прямой (Direct & Value focused)
                    [Текст сообщения]
                    ====SEPARATOR====
                    Вариант 2: Мягкий (Consultative/Question approach)
                    [Текст сообщения]
                    ====SEPARATOR====
                    Вариант 3: Отработка текущего решения (Competitor handling / Status quo challenge)
                    [Текст сообщения]
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"ИСТОРИЯ GETSALES:\n{lead_history}"}
                        ],
                        temperature=0.7
                    )
                    
                    raw_text = response.choices[0].message.content
                    variants = [v.strip() for v in raw_text.split("====SEPARATOR====") if v.strip()]
                    
                    for i, variant in enumerate(variants):
                        st.markdown(f'<div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 16px; color: #1E293B;"><strong style="color:#2563EB;">Вариант {i+1}</strong><br><br>{variant}</div>', unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Ошибка при обращении к OpenAI: {e}")
