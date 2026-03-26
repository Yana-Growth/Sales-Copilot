import streamlit as st
import os
import pypdf
import pandas as pd
import requests
import re

st.set_page_config(page_title="Tumodo Sales Copilot", layout="wide", page_icon="💼")

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; }
    [data-testid="stSidebar"] { background-color: #1E293B; color: white !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label { color: white !important; }
    div[data-baseweb="select"] * { color: black !important; }
    .stTextInput input, .stTextArea textarea { border-radius: 8px !important; color: black !important; background-color: white !important; }
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
        "Выбор модели",
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
    
    opponent_context = st.text_input("👤 О собеседнике (Необязательно)", placeholder="Например: Недавно перешел в эту компанию, любит строго по делу, CFO")
    company_context = st.text_input("🏢 О компании (Необязательно)", placeholder="Например: Внедряют SAP, 500+ сотрудников, открыли ИТ-хаб в Дубае")
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
                    kb_context = ""
                    for label, text in kb_texts.items():
                        if text:
                            kb_context += f"--- {label} ---\n{text[:3000]}\n\n"
                            
                    system_prompt = f"""
                    Ты — Стас Клюев (Stanislav Klyuy), Senior Enterprise Sales Executive в компании Tumodo (B2B).
                    Мы общаемся от лица Стаса Клюева. Твоя главная цель — квалифицировать лида в LinkedIn и закрыть его на звонок/демо.
                    
                    ВВОДНЫЕ О ЛИДЕ И СДЕЛКЕ:
                    - Портрет собеседника: {opponent_context if opponent_context else "Нет дополнительных данных"}
                    - Контекст компании: {company_context if company_context else "Нет дополнительных данных"}
                    - Регион: {region}
                    
                    ИСТОРИЯ ПЕРЕПИСКИ:
                    {lead_history}
                    
                    ЗАДАЧА:
                    Проигнорируй весь технический шум (Pipeline Stage, Automation Connect, Tags added).
                    1. ОПРЕДЕЛИ КОНТЕКСТ: Кто написал последнее смысловое сообщение? Стас Клюев или Лид?
                    2. СЦЕНАРИЙ А (Последнее слово за Лидом): Твоя задача написать 3 отличных варианта ответа.
                    3. СЦЕНАРИЙ Б (Последнее слово за Стасом / Лид молчит): Твоя задача написать 3 ненавязчивых фоллоу-апа (bump). Вытащи из контекста (или из таблиц конкурентов) точечную ценность (например, кейс про НДС, ROI, автоматизацию), чтобы вернуть лида в диалог.
                    4. ИСПОЛЬЗУЙ CHAIN OF THOUGHT: Перед тем как писать варианты, проведи краткий анализ (кто писал последним, какие боли мы закроем, был ли упомянут конкурент).
                    
                    ПРАВИЛА TUMODO:
                    - Будь уверенным, говори на языке бизнеса. Подписывайся как Stas Klyuy.
                    - НИКАКИХ извинений в начале. Используй consultative selling (спроси один точный вопрос в конце).
                    - РАБОТА С КОНКУРЕНТАМИ: Если клиент называет конкурента или мы знаем его из контекста (например, Concur, TravelPerk, Корпоративные карты), ТЫ ОБЯЗАН найти этого конкурента в таблице из Базы Знаний. Используй СТРОГО те слабые стороны конкурента и те сильные стороны Tumodo, которые прописаны в этой таблице! НЕ выдумывай общие аргументы, бери их строго из таблицы конкурентов.
                    - ПРАВИЛО ОТКАЗОВ: Если лид ЖЕСТКО отказывает (пишет "Не интересно", "Нет бюджетов", "Отстаньте"), НЕ ПЫТАЙСЯ ЕМУ ПРОДАВАТЬ. Выдай 3 варианта ОЧЕНЬ КОРОТКОГО (1-2 предложения) вежливого ответа: поблагодари за уделенное время, пожелай отличной недели и оставь микро-зацепку на будущее.
                    
                    БАЗА ЗНАНИЙ (СТРОГО ОПИРАЙСЯ НА ТАБЛИЦУ КОНКУРЕНТОВ ПРИ ОТВЕТАХ ПРО НИХ):
                    {kb_context}
                    
                    ОБЯЗАТЕЛЬНО: Раздели все логические блоки строго строкой "====SEPARATOR====".
                    
                    ФОРМАТ ОТВЕТА (Соблюдай сепараторы!):
                    Анализ:
                    [Твой краткий анализ: кто писал последним, что используем из базы знаний, какой подход выберем]
                    ====SEPARATOR====
                    Вариант 1: Короткий и прямой (Direct)
                    [Текст]
                    ====SEPARATOR====
                    Вариант 2: Мягкий (Consultative)
                    [Текст]
                    ====SEPARATOR====
                    Вариант 3: Отработка решения (Competitor challenge / Value Bump)
                    [Текст]
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={api_key}"
                    headers = {'Content-Type': 'application/json'}
                    data = {
                        "contents": [{"parts": [{"text": system_prompt}]}],
                        "generationConfig": {"temperature": 0.5}
                    }
                    
                    response = requests.post(url, headers=headers, json=data, timeout=45)
                    
                    if response.status_code != 200:
                        st.error(f"Ошибка API (Код {response.status_code}): {response.text}")
                    else:
                        resp_json = response.json()
                        if 'candidates' not in resp_json or not resp_json['candidates']:
                            st.error(f"Google заблокировал ответ (Safety filter): {resp_json}")
                        else:
                            raw_text = resp_json['candidates'][0]['content']['parts'][0].get('text', '')
                            
                            parts = [v.strip() for v in raw_text.split("====SEPARATOR====") if v.strip()]
                            
                            if len(parts) > 0:
                                with st.expander("🧠 Логика мышления ИИ (Анализ)", expanded=True):
                                    st.markdown(parts[0])
                                
                                for i, variant in enumerate(parts[1:]):
                                    st.markdown(f'<div style="background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 16px; color: #1E293B;"><strong style="color:#2563EB;">Вариант {i+1}</strong><br><br>{variant}</div>', unsafe_allow_html=True)
                            else:
                                st.write(raw_text)
                                
                except requests.exceptions.Timeout:
                    st.error("⏳ Серверы Google не ответили за 45 секунд. Скорее всего сервер перегружен, попробуйте отправить запрос еще раз.")
                except Exception as e:
                    st.error(f"Неизвестная ошибка: {e}")
