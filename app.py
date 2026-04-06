import os
import requests
import streamlit as st
import json
import uuid
from datetime import datetime
from groq import Groq

# ─── КОНФИГУРАЦИЯ ───────────────────────────────────────────────
TMDB_KEY = os.getenv("TMDB_API_KEY", "237a14ba3d35dc8e9a31103ab9eb449f")
GROQ_KEY = os.getenv("GROQ_API_KEY", "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")
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

client = Groq(api_key=GROQ_KEY)

SECTIONS = {
    "liked":   ("❤️", "Понравившиеся"),
    "watched": ("👀", "Просмотренные"),
    "planned": ("📌", "Запланированные"),
}

# ─── CSS ────────────────────────────────────────────────────────
CUSTOM_CSS = """ . . . """
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>

/* === ШРИФТ === */
html, body, [class*="css"] {
    font-family: "JetBrains Mono", monospace !important;
}

/* === ЦВЕТА (OKLCH-подобная тема) === */
:root {
  --background: #0f0b1a;
  --foreground: #f4f4f5;
  --card: #18122b;
  --primary: #d946ef;
  --secondary: #27203f;
  --muted: #a1a1aa;
  --border: #2e2645;
  --input: #31274f;
  --radius: 10px;
}

/* === ОСНОВНОЙ ФОН === */
html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% 20%, #1a1333, #0f0b1a 60%) !important;
    color: var(--foreground);
}

/* === САЙДБАР === */
[data-testid="stSidebar"] {
    background: var(--card) !important;
    border-right: 1px solid var(--border) !important;
}

/* === ТЕКСТ === */
h1, h2, h3, p, span {
    color: var(--foreground) !important;
}

/* === КНОПКИ === */
.stButton > button {
    background: var(--primary) !important;
    color: white !important;
    border-radius: var(--radius) !important;
    border: none !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    background: #c026d3 !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(217, 70, 239, 0.3);
}

/* === ИНПУТЫ === */
.stTextInput input,
.stTextArea textarea {
    background: var(--input) !important;
    border: 1px solid var(--border) !important;
    color: white !important;
    border-radius: var(--radius) !important;
}

/* === ЧАТ === */
.chat-wrap {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    max-height: 480px;
    overflow-y: auto;
}

.chat-bubble-user {
    background: var(--primary);
    color: white;
    border-radius: 14px 14px 4px 14px;
    padding: 10px 14px;
    margin: 8px 0 8px 60px;
}

.chat-bubble-ai {
    background: var(--secondary);
    border: 1px solid var(--border);
    color: var(--foreground);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 14px;
    margin: 8px 60px 8px 0;
}

/* === КАРТОЧКИ / EXPANDER === */
[data-testid="stExpander"] {
    background: var(--secondary);
    border-radius: var(--radius);
    border: 1px solid var(--border);
}

/* === СКРОЛЛ === */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-thumb {
    background: #3b2f63;
    border-radius: 10px;
}

</style>
"""

# ─── МОДЕЛЬ GROQ ────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_model() -> str:
    try:
        models = client.models.list()
        preferred = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ]
        available = [m.id for m in models.data]
        for m in preferred:
            if m in available:
                return m
        return available[0] if available else "llama-3.3-70b-versatile"
    except:
        return "llama-3.3-70b-versatile"

# ─── ХРАНИЛИЩЕ С ПЕРСОНАЛЬНЫМ USER ID ────────────────────────────
def get_user_id() -> str:
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())[:8]
    return st.session_state.user_id

def read_collection() -> dict:
    user_id = get_user_id()
    storage_file = f"collection_{user_id}.json"
    
    if os.path.exists(storage_file):
        with open(storage_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {key: [] for key in SECTIONS}

def write_collection() -> None:
    user_id = get_user_id()
    storage_file = f"collection_{user_id}.json"
    
    with open(storage_file, "w", encoding="utf-8") as f:
        json.dump(st.session_state.collection, f, ensure_ascii=False, indent=2)

# ─── TMDB ───────────────────────────────────────────────────────
def tmdb_request(endpoint: str, **params) -> dict:
    params.update({"api_key": TMDB_KEY, "language": "ru-RU"})
    try:
        r = requests.get(f"{TMDB_BASE}/{endpoint}", params=params, timeout=8)
        r.raise_for_status()
        return r.json()
    except:
        return {}

@st.cache_data(ttl=600)
def fetch_popular(page: int = 1, content_type: str = "movie") -> list:
    return tmdb_request(f"{content_type}/popular", page=page).get("results", [])

@st.cache_data(ttl=300)
def fetch_search(query: str, content_type: str = "movie") -> list:
    return tmdb_request(f"search/{content_type}", query=query).get("results", [])

@st.cache_data(ttl=300)
def fetch_search_tv(query: str) -> list:
    return tmdb_request("search/tv", query=query).get("results", [])

# ─── КОЛЛЕКЦИЯ ──────────────────────────────────────────────────
def movie_in_section(movie_id: int, section: str) -> bool:
    return any(m["id"] == movie_id for m in st.session_state.collection[section])

def toggle_movie(movie: dict, section: str) -> None:
    col = st.session_state.collection[section]
    icon, name = SECTIONS[section]
    if movie_in_section(movie["id"], section):
        st.session_state.collection[section] = [m for m in col if m["id"] != movie["id"]]
        st.toast(f"✕ Удалено из «{name}»")
    else:
        col.append(movie)
        st.toast(f"{icon} Добавлено в «{name}»")
    write_collection()

def format_collection_for_ai() -> str:
    """Форматирует всю коллекцию пользователя для системного промпта ИИ."""
    c = st.session_state.collection
    lines = []

    for key, (icon, label) in SECTIONS.items():
        if c.get(key):
            lines.append(f"{icon} {label.upper()}:")
            for item in c[key]:
                title = item.get("title") or item.get("name", "—")
                date = item.get("release_date") or item.get("first_air_date", "")
                year = date[:4] if date else "?"
                rating = item.get("vote_average", 0)
                overview = item.get("overview", "")[:80]
                lines.append(f"  • {title} ({year}) ⭐{rating:.1f} — {overview}")
            lines.append("")

    return "\n".join(lines) if lines else "Коллекция пуста."

# ─── ИИ ─────────────────────────────────────────────────────────
def build_system_prompt(mode: str) -> str:
    collection_text = format_collection_for_ai()

    base = f"""Ты — персональный ИИ-помощник по фильмам и сериалам.
Отвечай ТОЛЬКО на русском языке. Будь кратким и конкретным.

КОЛЛЕКЦИЯ ПОЛЬЗОВАТЕЛЯ (используй её при рекомендациях):
{collection_text}
"""
    if mode == "search":
        base += "\nРежим: пользователь хочет найти конкретный фильм/сериал по описанию, актёрам или сюжету. Уточняй детали и предлагай варианты."
    else:
        base += "\nРежим: пользователь хочет рекомендации. Учитывай его вкусы из коллекции. Не предлагай то, что он уже смотрел или лайкнул. Задавай уточняющие вопросы о жанре, настроении, эпохе."
    return base

def chat_with_ai(user_message: str, history: list, mode: str) -> str:
    """
    БАГ ИСПРАВЛЕН: история передаётся без текущего сообщения пользователя
    (оно добавляется в историю уже ПОСЛЕ получения ответа в show_ai_chat).
    """
    try:
        model = get_model()
        messages = [{"role": "system", "content": build_system_prompt(mode)}]

        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка Groq: {e}"

def extract_titles_and_search(ai_text: str) -> list:
    """ИИ извлекает названия + английские переводы, ищем в TMDB."""
    try:
        model = get_model()
        prompt = f"""Из текста ниже извлеки названия фильмов и сериалов.
Для каждого названия дай ОРИГИНАЛЬНОЕ (английское) название если знаешь.
Формат ответа — строго одна строка на фильм:
РУССКОЕ НАЗВАНИЕ | АНГЛИЙСКОЕ НАЗВАНИЕ

Если английское неизвестно, пиши только русское без символа |

Текст:
{ai_text}"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()

        results = []
        seen_ids = set()

        for line in raw.split("\n"):
            line = line.strip().lstrip("•-–—*#").strip()
            if not line or len(line) < 2:
                continue

            if "|" in line:
                parts = line.split("|")
                ru_title = parts[0].strip()
                en_title = parts[1].strip()
                search_queries = [en_title, ru_title]
            else:
                search_queries = [line]

            found = None
            for query in search_queries:
                if not query:
                    continue
                for ctype in ("tv", "movie"):
                    results_raw = fetch_search(query, ctype)
                    if results_raw:
                        candidate = results_raw[0]
                        if candidate["id"] not in seen_ids:
                            found = candidate
                            break
                if found:
                    break

            if found:
                seen_ids.add(found["id"])
                results.append(found)

        return results

    except Exception as e:
        st.error(f"Ошибка извлечения: {e}")
        return []

# ─── КАРТОЧКИ ───────────────────────────────────────────────────
def render_movie_card(movie: dict, col, content_type: str = "movie") -> None:
    with col:
        poster = movie.get("poster_path")
        if poster:
            st.image(POSTER_BASE + poster, use_container_width=True)
        else:
            st.markdown("🎞️ *Нет постера*")

        title = movie.get("title") or movie.get("name", "—")
        date  = movie.get("release_date") or movie.get("first_air_date", "")
        year  = f"({date[:4]})" if date else ""
        rating = movie.get("vote_average", 0)

        st.markdown(f"**{title}** {year}")
        st.caption(f"⭐ {rating:.1f}  •  🗳 {movie.get('vote_count', 0)}")

        overview = movie.get("overview", "")
        if overview:
            with st.expander("📖"):
                st.write(overview[:350] + ("…" if len(overview) > 350 else ""))

        bcols = st.columns(3)
        for idx, (key, (icon, label)) in enumerate(SECTIONS.items()):
            active = movie_in_section(movie["id"], key)
            with bcols[idx]:
                if st.button(
                    "✅" if active else icon,
                    key=f"{key}_{movie['id']}_{content_type}",
                    help=label,
                    use_container_width=True,
                ):
                    toggle_movie(movie, key)

def render_grid(movies: list, content_type: str = "movie") -> None:
    if not movies:
        st.info("Ничего не найдено.")
        return
    st.caption(f"Найдено: {len(movies)}")
    cols = st.columns(4)
    for i, film in enumerate(movies):
        render_movie_card(film, cols[i % 4], content_type)

# ─── ЧАТ ────────────────────────────────────────────────────────
def show_ai_chat(mode: str) -> None:
    hist_key    = f"chat_history_{mode}"
    pending_key = f"pending_{mode}"
    input_key   = f"chat_input_{mode}"

    first_msg = (
        "Привет! 👋 Опиши фильм или сериал — сюжет, актёров, жанр, что помнишь."
        if mode == "search"
        else "Привет! 👋 Расскажи, что хочешь посмотреть: жанр, настроение, эпоха?"
    )

    if hist_key not in st.session_state:
        st.session_state[hist_key] = [{"role": "ai", "content": first_msg}]
    if pending_key not in st.session_state:
        st.session_state[pending_key] = None

    history = st.session_state[hist_key]

    # ── обработка pending сообщения ──
    if st.session_state[pending_key]:
        user_text = st.session_state[pending_key]
        st.session_state[pending_key] = None

        # БАГ ИСПРАВЛЕН: сначала получаем ответ, потом добавляем в историю
        with st.spinner("🤖 Думаю..."):
            ai_reply = chat_with_ai(user_text, history, mode)

        history.append({"role": "user", "content": user_text})
        history.append({"role": "ai", "content": ai_reply})
        st.rerun()

    # ── вывод истории ──
    chat_html = '<div class="chat-wrap">'
    for msg in history:
        if msg["role"] == "user":
            chat_html += f'<div class="chat-bubble-user">👤 {msg["content"]}</div>'
        else:
            chat_html += f'<div class="chat-bubble-ai">🤖 {msg["content"]}</div>'
    chat_html += "</div>"
    st.markdown(chat_html, unsafe_allow_html=True)

    def on_submit():
        val = st.session_state.get(input_key, "").strip()
        if val:
            st.session_state[pending_key] = val
            st.session_state[input_key] = ""

    st.text_input(
        "Сообщение",
        placeholder="Напиши сообщение и нажми Enter…",
        label_visibility="collapsed",
        key=input_key,
        on_change=on_submit,
    )

    st.divider()
    if st.button("🎬 Найти рекомендованные фильмы", use_container_width=True, key=f"find_{mode}"):
        if len(history) > 1:
            full_context = "\n".join(m["content"] for m in history)
            with st.spinner("🔍 Подбираю фильмы по всему диалогу…"):
                movies = extract_titles_and_search(full_context)
            if movies:
                st.subheader("🎬 Рекомендованные фильмы")
                render_grid(movies)
            else:
                st.warning("Не нашёл конкретных фильмов — уточни запрос в чате.")
        else:
            st.info("Сначала пообщайся с ИИ — расскажи что хочешь посмотреть.")

    if st.button("🗑 Очистить чат", use_container_width=True, key=f"clear_{mode}"):
        st.session_state[hist_key] = [{"role": "ai", "content": first_msg}]
        st.rerun()

# ─── СТРАНИЦЫ ───────────────────────────────────────────────────

def trigger_search():
    # БАГ ИСПРАВЛЕН: .strip() с вызовом скобок; сбрасываем chat_mode
    val = st.session_state.get("main_search", "").strip()
    if val:
        st.session_state.search_triggered = True
        st.session_state.chat_mode = None  # скрываем чат при ручном поиске


def page_home() -> None:
    st.markdown("""
    <div style="background:rgba(61,37,99,0.3);border:2px solid #6b4c9a;border-radius:16px;padding:20px;margin-bottom:24px;">
        <h3 style="margin:0 0 8px;">🎬 ReeSeeAI</h3>
        <p style="margin:0;color:#b8a5d1;">Найди фильм по описанию или получи персональные рекомендации от ИИ</p>
    </div>
    """, unsafe_allow_html=True)

    search_query = st.text_input(
        "",
        placeholder="Быстрый поиск по названию…",
        label_visibility="collapsed",
        key="main_search",
        on_change=trigger_search,  # БАГ ИСПРАВЛЕН: ссылка на функцию, без ()
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Найти по описанию", use_container_width=True, key="btn_search"):
            st.session_state.chat_mode = "search"
            st.session_state.search_triggered = False
            st.rerun()
    with col2:
        if st.button("✨ Подобрать по критериям", use_container_width=True, key="btn_recommend"):
            st.session_state.chat_mode = "recommend"
            st.session_state.search_triggered = False
            st.rerun()

    mode = st.session_state.get("chat_mode")

    if mode in ("search", "recommend"):
        title = "🔍 Найти фильм по описанию" if mode == "search" else "✨ Рекомендации"
        st.subheader(title)
        show_ai_chat(mode)
    elif st.session_state.get("search_triggered") and search_query:
        st.divider()
        col_m, col_t = st.columns(2)
        movies = fetch_search(search_query, "movie")
        tvs    = fetch_search(search_query, "tv")
        if movies:
            with col_m:
                st.subheader("🎬 Фильмы")
                render_grid(movies, "movie")
        if tvs:
            with col_t:
                st.subheader("📺 Сериалы")
                render_grid(tvs, "tv")
        if not movies and not tvs:
            st.info("Ничего не найдено.")


def page_section(section_key: str) -> None:
    icon, label = SECTIONS[section_key]
    items = st.session_state.collection[section_key]
    st.markdown(f"<h1>{icon} {label}</h1>", unsafe_allow_html=True)
    st.caption(f"Всего: {len(items)}")
    if items:
        render_grid(items)
    else:
        st.info("Список пуст — добавляй с главной страницы!")

# ─── ИНИЦИАЛИЗАЦИЯ ──────────────────────────────────────────────
st.set_page_config(page_title="🎬 Кинотека", layout="wide", page_icon="🎬")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

if "collection" not in st.session_state:
    st.session_state.collection = read_collection()
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = None
if "search_triggered" not in st.session_state:
    st.session_state.search_triggered = False  # БАГ ИСПРАВЛЕН: было search_trigggered (3 'g')

# ─── САЙДБАР ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;margin-bottom:20px;">
        <div style="width:70px;height:70px;background:linear-gradient(135deg,#9d69d5,#6b4c9a);
            border-radius:16px;margin:0 auto 12px;display:flex;align-items:center;
            justify-content:center;font-size:32px;">🎬</div>
        <p style="color:#b8a5d1;font-size:0.9em;">Персональная кинотека с ИИ-рекомендациями</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "Раздел",
        ["🏠 Главная", "❤️ Понравившиеся", "👀 Просмотренные", "📌 Запланированные"],
        label_visibility="collapsed",
    )

    st.divider()

    c = st.session_state.collection
    st.markdown(f"""
    <div style="background:#3d2563;border:1px solid #6b4c9a;border-radius:12px;padding:12px;text-align:center;">
        <p style="margin:0 0 8px;font-weight:600;color:#c59dff;">📊 Моя статистика</p>
        <p style="margin:2px 0;font-size:13px;">❤️ {len(c.get('liked',[]))} понравилось</p>
        <p style="margin:2px 0;font-size:13px;">👀 {len(c.get('watched',[]))} просмотрено</p>
        <p style="margin:2px 0;font-size:13px;">📌 {len(c.get('planned',[]))} запланировано</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"""
    <div style="background:#6b4c9a;border:2px solid #9d69d5;border-radius:12px;padding:14px;text-align:center;">
        <div style="width:50px;height:50px;background:#ff6b35;border-radius:50%;
            margin:0 auto 8px;display:flex;align-items:center;justify-content:center;
            font-weight:bold;font-size:24px;color:white;">N</div>
        <p style="margin:4px 0;font-weight:600;font-size:14px;">noffnight</p>
        <p style="margin:0;color:#b8a5d1;font-size:0.85em;">noffnight@github.com</p>
    </div>
    """, unsafe_allow_html=True)

# ─── РОУТИНГ ────────────────────────────────────────────────────
if "Главная" in page:
    page_home()
elif "Понравившиеся" in page:
    page_section("liked")
elif "Просмотренные" in page:
    page_section("watched")
elif "Запланированные" in page:
    page_section("planned")
