import streamlit as st
import os
import pypdf
import pandas as pd
import requests
import re
import time

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
        text = ""
        try:
            if filename.endswith(('.csv', '.xlsx')):
                df = pd.read_csv(filename) if filename.endswith('.csv') else pd.read_excel(filename)
                text = df.to_string()
            elif filename.endswith('.txt'):
                with open(filename, 'r', encoding='utf-8') as f:
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
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-8b",
            "gemini-pro"
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
            with st.spinner("🚀 Молниеносный запуск: Анализирую базу знаний и пишу ответ..."):
                try:
                    # ПОДГОТОВКА СВОДНОГО КОНТЕКСТА: ТОЛЬКО ЛЕГКИЕ TXT И XLSX
                    kb_context = "СКОМПИЛИРОВАННАЯ БАЗА ЗНАНИЙ (ОБЯЗАТЕЛЬНО К ИСПОЛЬЗОВАНИЮ):\n"
                    for label, text in kb_texts.items():
                        if text: kb_context += f"--- {label} ---\n{text}\n\n"
                    
                    # ГЕНЕРАЦИЯ ОТВЕТА
                    system_prompt = f"""
                    Ты — Стан Клюев (Stan Klyuy), Senior Enterprise Sales Executive в компании Tumodo (B2B).
                    Мы общаемся от лица Stan Klyuy. Твоя главная цель — квалифицировать лида в LinkedIn и закрыть его на звонок/демо.
                    
                    ВВОДНЫЕ О ЛИДЕ И СДЕЛКЕ:
                    - Портрет собеседника: {opponent_context if opponent_context else "Нет дополнительных данных"}
                    - Контекст компании: {company_context if company_context else "Нет дополнительных данных"}
                    - Регион: {region}
                    
                    ИСТОРИЯ ПЕРЕПИСКИ:
                    {lead_history}
                    
                    ЗАДАЧА:
                    Проигнорируй весь технический шум (Pipeline Stage, Automation Connect, Tags added).
                    1. ОПРЕДЕЛИ КОНТЕКСТ: Кто написал последнее смысловое сообщение? Stan Klyuy или Лид?
                    2. СЦЕНАРИЙ А (Последнее слово за Лидом): Твоя задача написать 3 отличных варианта ответа.
                    3. СЦЕНАРИЙ Б (Последнее слово за Stan / Лид молчит): Твоя задача написать 3 ненавязчивых фоллоу-апа (bump). Вытащи из контекста точечную ценность (например, кейс про НДС, ROI, автоматизацию), чтобы вернуть лида в диалог.
                    4. ИСПОЛЬЗУЙ CHAIN OF THOUGHT: Перед тем как писать варианты, проведи краткий анализ (кто писал последним, какие боли мы закроем, был ли упомянут конкурент).
                    
                    ПРАВИЛА TUMODO (ТОН ОФ ВОЙС):
                    - Будь уверенным, говори на языке бизнеса. Подписывайся строго как Stan.
                    - НИКАКИХ извинений в начале. Используй consultative selling (спроси один точный вопрос в конце).
                    - РАБОТА С КОНКУРЕНТАМИ: Если клиент использует конкурента (например, Concur, TravelPerk, Корпоративные карты), ТЫ ОБЯЗАН найти этого конкурента в таблице из Базы Знаний. Используй СТРОГО те слабые стороны конкурента и те сильные стороны Tumodo, которые прописаны в этой таблице! НЕ выдумывай общие аргументы.
                    - ПРАВИЛО ОТКАЗОВ: Если лид ЖЕСТКО отказывает (пишет "Не интересно", "Нет бюджетов", "Отстаньте"), НЕ ПЫТАЙСЯ ЕМУ ПРОДАВАТЬ. Выдай 3 варианта ОЧЕНЬ КОРОТКОГО (1-2 предложения) вежливого ответа: поблагодари за уделенное время, пожелай отличной недели и оставь микро-зацепку на будущее.
                    - ГОРЯЧИЕ (WARM) ЛИДЫ: Если лид ПРЯМО ПИШЕТ, ЧТО ЗАИНТЕРЕСОВАН (например, "Давайте созвонимся", "Звучит интересно", "Можем пообщаться"), ты ОБЯЗАН предложить короткий звонок на 10-15 минут и СПРОСИТЬ НОМЕР ТЕЛЕФОНА (WhatsApp/Phone number), чтобы быстро назначить встречу. Не затягивай переписку.
                    - ВЫБОР ЯЗЫКА ОТВЕТА: Всегда генерируй финальные варианты ответов (Варианты 1, 2, 3) СТРОГО НА АНГЛИЙСКОМ ЯЗЫКЕ (или на языке собеседника: если лид пишет по-немецки, отвечай по-немецки; если по-арабски — по-арабски). Твой анализ можешь выдавать на русском языке.
                    
                    БАЗА ЗНАНИЙ (ОПИРАЙСЯ НА ЭТИ ДАННЫЕ):
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
                    """
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={api_key}"
                    headers = {'Content-Type': 'application/json'}
                    data = {
                        "contents": [{"parts": [{"text": system_prompt}]}],
                        "generationConfig": {"temperature": 0.5}
                    }
                    
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        response = requests.post(url, headers=headers, json=data, timeout=120)
                        if response.status_code == 503:
                            if attempt < max_attempts - 1:
                                st.warning(f"⚠️ Сервер Google перегружен (Ошибка 503). Жду 3 секунды и пробую еще раз... (Попытка {attempt+1} из {max_attempts})")
                                time.sleep(3)
                                continue
                        break
                    
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
                    st.error("⏳ Серверы Google не ответили за 2 минуты. Скорее всего сервер перегружен.")
                except Exception as e:
                    st.error(f"Неизвестная ошибка: {e}")
