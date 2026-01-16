# -*- coding: utf-8 -*-
import os
import re
from typing import Optional, List, Tuple

import streamlit as st

# OpenAI SDK v1+
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# =========================
# Page config
# =========================
st.set_page_config(
    page_title="BGGovAI интелигентен съветник",
    page_icon="🇧🇬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_TITLE = "BGGovAI интелигентен съветник"
APP_SUBTITLE = "За граждани и бизнес • администрация, закони и услуги (само България) • човешки, институционален тон"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


# =========================
# UI: premium, readable, no blur
# =========================
st.markdown("""
<style>
  :root{
    --bg:#f6f8fb;
    --card:#ffffff;
    --text:#0f172a;
    --muted:#475569;
    --border: rgba(15,23,42,.10);
    --shadow: 0 10px 28px rgba(2,6,23,.08);
    --shadow2: 0 16px 40px rgba(2,6,23,.10);
    --accent:#0b3a66;
    --accent2:#0ea5a4;
  }
  .stApp { background: var(--bg) !important; }
  header[data-testid="stHeader"] { background: transparent !important; }
  section.main > div { padding-top: 1.0rem; }

  .gov-header{
    border-radius: 18px;
    overflow: hidden;
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    margin-bottom: 14px;
  }
  .flag{
    height: 10px;
    background: linear-gradient(to bottom,
      #ffffff 0%, #ffffff 33%,
      #00966E 33%, #00966E 66%,
      #D62612 66%, #D62612 100%);
  }
  .gov-top{
    display:flex; gap:14px; align-items:center;
    padding: 14px 16px;
    background: var(--card);
  }
  .crest{
    width: 54px; height: 54px;
    border-radius: 14px;
    display:flex; align-items:center; justify-content:center;
    background: linear-gradient(180deg, rgba(11,58,102,.10), rgba(11,58,102,.04));
    border: 1px solid rgba(11,58,102,.18);
    font-weight: 900;
    font-size: 22px;
  }
  .gov-title h1{
    margin: 0;
    font-size: 20px;
    font-weight: 900;
    letter-spacing: -0.2px;
    color: var(--text);
  }
  .gov-title p{
    margin: 5px 0 0 0;
    font-size: 13px;
    color: var(--muted);
  }

  .card{
    border-radius: 16px;
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    padding: 12px 14px;
    margin: 10px 0;
  }
  .card:hover{ box-shadow: var(--shadow2); transition: 160ms ease; }

  .section-title{
    font-weight: 900;
    letter-spacing: -0.2px;
    color: var(--text);
    margin: 0 0 6px 0;
    font-size: 16px;
  }
  .small{
    color: var(--muted);
    font-size: 12.5px;
    margin: 0;
    line-height: 1.55;
  }

  .summary{
    border-left: 5px solid rgba(14,165,164,.55);
    background: linear-gradient(180deg, rgba(14,165,164,.08), rgba(14,165,164,.03));
  }
  .followup{
    border-left: 5px solid rgba(11,58,102,.55);
    background: linear-gradient(180deg, rgba(11,58,102,.08), rgba(11,58,102,.03));
  }
  .sources{
    border-left: 5px solid rgba(15,23,42,.18);
    background: rgba(15,23,42,.02);
  }

  .chip{
    display:inline-flex; align-items:center; gap:8px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(11,58,102,.06);
    border: 1px solid rgba(11,58,102,.14);
    font-size: 12px;
    color: rgba(15,23,42,.86);
    margin-right: 6px;
    margin-bottom: 6px;
  }

  .hint{
    color: rgba(71,85,105,.9);
    font-size: 12.5px;
    margin-top: 6px;
    margin-bottom: 8px;
  }

  div[data-testid="stToggleSwitch"] label { font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="gov-header">
  <div class="flag"></div>
  <div class="gov-top">
    <div class="crest">🇧🇬</div>
    <div class="gov-title">
      <h1>BGGovAI интелигентен съветник</h1>
      <p>За граждани и бизнес • администрация, закони и услуги (само България)</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# =========================
# Session state (stability)
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user"/"assistant","content":...}]
if "history" not in st.session_state:
    st.session_state.history = []    # [(title, question)]
if "last_debug" not in st.session_state:
    st.session_state.last_debug = {}


# =========================
# UI helpers
# =========================
def ui_card(title: str, body_md: str, variant: str = "card"):
    st.markdown(f"""
    <div class="card {variant}">
      <div class="section-title">{title}</div>
      <div class="small">{body_md}</div>
    </div>
    """, unsafe_allow_html=True)

def ui_summary(summary_md: str):
    ui_card("Резюме", summary_md, variant="summary")

def ui_followup(question_md: str):
    ui_card("За да продължа точно", question_md, variant="followup")

def ui_sources(items: List[Tuple[str, str]]):
    links = "\n".join([f"- [{n}]({u})" for n, u in items])
    st.markdown(f"""
    <div class="card sources">
      <div class="section-title">Официални държавни институции</div>
      <div class="small">{links}</div>
    </div>
    """, unsafe_allow_html=True)

def make_title(question: str) -> str:
    t = (question or "").lower()
    if any(k in t for k in ["кат", "книжк", "точк", "пътна полиция", "фиш", "акт", "глоб", "регистрац", "талон", "птп"]):
        return "🚗 КАТ / Пътна полиция"
    if any(k in t for k in ["нап", "данък", "данъци", "декларац", "ревиз", "задължен", "осигуровк"]):
        return "💼 НАП"
    if any(k in t for k in ["нои", "пенси", "болнич", "обезщет", "осигурител", "стаж", "майчин"]):
        return "👥 НОИ"
    if any(k in t for k in ["еоод", "оод", "мол", "управител", "а4", "търговски регист", "вписван", "агенция по вписвания"]):
        return "🧾 Търговски регистър"
    if any(k in t for k in ["закон", "чл", "ал.", "проектозакон", "държавен вестник", "обнарод", "наредб", "правилник"]):
        return "⚖️ Закони"
    return "ℹ️ Общ въпрос"
# =========================
# Institutions router (central administration only)
# =========================
def render_sources(hint: str) -> List[Tuple[str, str]]:
    t = (hint or "").lower()

    ALL = [
        ("Министерски съвет", "https://www.gov.bg/"),
        ("Народно събрание", "https://www.parliament.bg/"),
        ("Държавен вестник", "https://dv.parliament.bg/"),
        ("Министерство на електронното управление", "https://www.megov.bg/"),
        ("Електронно управление (eGov)", "https://egov.bg/"),
        ("Министерство на вътрешните работи (МВР)", "https://www.mvr.bg/"),
        ("КАТ / Пътна полиция (МВР)", "https://www.mvr.bg/"),
        ("НАП", "https://nra.bg/"),
        ("НОИ", "https://www.nssi.bg/"),
        ("Министерство на финансите", "https://www.minfin.bg/"),
        ("Българска народна банка", "https://www.bnb.bg/"),
        ("Национален статистически институт", "https://www.nsi.bg/"),
        ("Министерство на правосъдието", "https://www.justice.government.bg/"),
        ("Агенция по вписванията / Търговски регистър", "https://portal.registryagency.bg/"),
        ("Агенция по вписванията / Имотен регистър", "https://portal.registryagency.bg/"),
        ("Министерство на труда и социалната политика", "https://www.mlsp.government.bg/"),
        ("Министерство на регионалното развитие и благоустройството", "https://www.mrrb.bg/"),
        ("Министерство на транспорта и съобщенията", "https://www.mtc.government.bg/"),
        ("Агенция „Пътна инфраструктура“ (АПИ)", "https://www.api.bg/"),
        ("ИА „Автомобилна администрация“", "https://rta.government.bg/"),
        ("Министерство на здравеопазването", "https://www.mh.government.bg/"),
        ("Министерство на образованието и науката", "https://www.mon.bg/"),
        ("Министерство на околната среда и водите", "https://www.moew.government.bg/"),
        ("Министерство на земеделието", "https://www.mzh.government.bg/"),
        ("Министерство на икономиката и индустрията", "https://www.mee.government.bg/"),
        ("Сметна палата", "https://www.bulnao.government.bg/"),
    ]

    def pick(names: set[str]) -> List[Tuple[str, str]]:
        return [x for x in ALL if x[0] in names]

    if any(k in t for k in ["кат", "пътна полиция", "шофьор", "книжк", "контролни точки", "фиш", "акт", "глоб", "регистрац", "талон", "птп"]):
        return pick({
            "Министерство на вътрешните работи (МВР)",
            "КАТ / Пътна полиция (МВР)",
            "Електронно управление (eGov)",
        })

    if any(k in t for k in ["нап", "данък", "данъци", "деклара", "осигуровк", "ревиз", "задължен"]):
        return pick({
            "НАП",
            "Министерство на финансите",
            "Електронно управление (eGov)",
        })

    if any(k in t for k in ["нои", "пенси", "болнич", "обезщет", "осигурител", "стаж", "майчин"]):
        return pick({
            "НОИ",
            "Министерство на труда и социалната политика",
            "Електронно управление (eGov)",
        })

    if any(k in t for k in ["еоод", "оод", "мол", "управител", "а4", "търговски регист", "вписван", "агенция по вписвания"]):
        return pick({
            "Агенция по вписванията / Търговски регистър",
            "Министерство на правосъдието",
            "Електронно управление (eGov)",
        })

    if any(k in t for k in ["имот", "възбра", "ипотек", "нотари", "имотен регист", "вписван"]):
        return pick({
            "Агенция по вписванията / Имотен регистър",
            "Министерство на правосъдието",
            "Електронно управление (eGov)",
        })

    if any(k in t for k in ["път", "винет", "тол", "апи", "магистра", "пътна инфраструктура"]):
        return pick({
            "Агенция „Пътна инфраструктура“ (АПИ)",
            "Министерство на регионалното развитие и благоустройството",
            "Министерство на транспорта и съобщенията",
        })

    if any(k in t for k in ["автомобилна администрация", "лиценз", "превоз", "такси", "камион", "автобус"]):
        return pick({
            "ИА „Автомобилна администрация“",
            "Министерство на транспорта и съобщенията",
        })

    if any(k in t for k in ["закон", "чл", "ал.", "проектозакон", "държавен вестник", "обнарод", "наредб", "правилник"]):
        return pick({
            "Народно събрание",
            "Държавен вестник",
            "Министерство на правосъдието",
        })

    return pick({
        "Министерски съвет",
        "Електронно управление (eGov)",
        "Народно събрание",
        "Държавен вестник",
    })


# =========================
# Intent + question shaping
# =========================
def classify_intent(q: str) -> str:
    t = (q or "").lower()
    if any(k in t for k in ["еоод", "оод", "мол", "управител", "а4", "търговски регист", "агенция по вписвания"]):
        return "ADMIN_MOL"
    if any(k in t for k in ["закон", "чл", "ал.", "проектозакон", "държавен вестник", "обнарод", "наредб", "правилник", "гражданств"]):
        return "LEGAL"
    if any(k in t for k in ["кат", "пътна полиция", "книжк", "точк", "фиш", "акт", "глоб", "регистрац", "птп"]):
        return "KAT"
    if any(k in t for k in ["нап", "данък", "данъци", "декларац", "осигуровк", "ревиз", "задължен"]):
        return "NAP"
    if any(k in t for k in ["нои", "пенси", "болнич", "обезщет", "осигурител", "стаж", "майчин"]):
        return "NOI"
    return "GENERAL"

def needs_clarification(q: str, intent: str) -> Optional[str]:
    t = (q or "").lower()

    if intent == "ADMIN_MOL":
        # Common ambiguity: has QES/KEP, change only manager or other circumstances too?
        return "Имаш ли КЕП за електронно подаване и сменяш ли само управител (МОЛ), или и други обстоятелства (адрес, предмет, капитал)?"

    if intent == "LEGAL":
        return "Имаш ли конкретния текст (чл./ал./§) или линк към проекта/Държавен вестник? Ако да – прати го, за да дам точен анализ."

    if intent == "KAT":
        # KAT questions often need scenario
        if any(k in t for k in ["глоб", "фиш", "акт"]) and not re.search(r"\b(серия|номер|дата)\b", t):
            return "Става ли дума за фиш или акт, и имаш ли дата/номер? (за да дам точните стъпки за проверка/обжалване)"
        if any(k in t for k in ["книжк", "свидетелств"]) and not any(k in t for k in ["подмяна", "изгуб", "открад", "изтич", "нов"]):
            return "Става дума за подмяна, изгубена/открадната книжка, или първо издаване?"
        return None

    if intent == "NAP":
        if "декларац" in t and not any(k in t for k in ["гдд", "чл. 50", "ддс", "осигур", "6", "1", "55"]):
            return "Коя декларация имаш предвид (напр. ГДД, ДДС, осигуровки), и физическо лице ли е или фирма?"
        return None

    if intent == "NOI":
        if "пенси" in t and not any(k in t for k in ["възраст", "стаж", "инвалид", "наслед", "учител", "ранно"]):
            return "За какъв вид пенсия става дума (възраст/стаж, инвалидна, наследствена и т.н.)?"
        return None

    return None
# =========================
# OpenAI client (stable)
# =========================
def get_openai_client() -> Optional["OpenAI"]:
    if OpenAI is None:
        return None
    key = None
    try:
        key = st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        key = None
    if not key:
        key = os.getenv("OPENAI_API_KEY", "").strip() or None
    if not key:
        return None
    try:
        return OpenAI(api_key=key)
    except Exception:
        return None

def get_model() -> str:
    try:
        return st.secrets.get("OPENAI_MODEL", DEFAULT_MODEL)
    except Exception:
        return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

@st.cache_data(ttl=900, show_spinner=False)
def ai_call(system: str, user: str, model: str) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ AI модулът не е активен (липсва OPENAI_API_KEY). Мога да дам ориентир и без ИИ, но без „умно“ персонализиране."
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        # Do not crash the app
        return f"❌ AI повикването не мина. Причина: {e}"

SYSTEM_PROMPT = """
Ти си BGGovAI — граждански съветник за България (само централна администрация).
Отговаряй на български, ясно, човешки, но институционално.

Правила:
- Давай подробен, структуриран отговор по подразбиране.
- Когато има несигурност/варианти: дай 2–3 алтернативи и задай 1 уточняващ въпрос.
- Не измисляй членове/алинии. Ако липсва конкретен текст — кажи какво да се провери и къде.
- Не твърди, че проверяваш „в реално време“, освен ако изрично е дадено.
- Формат на отговора:
  1) Резюме (2–3 реда)
  2) Стъпки
  3) Документи
  4) Подаване: онлайн (ако е налично) / на място
  5) Какво да провериш допълнително
  6) (по желание) Уточняващ въпрос
"""

# =========================
# Sidebar toggles (compact)
# =========================
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    check_sources = st.toggle("Провери източници", value=True)
with c2:
    show_debug = st.toggle("Техн. детайли", value=False)
with c3:
    pass

# History card (titles)
if st.session_state.history:
    st.markdown('<div class="card"><div class="section-title">История (сесия)</div>', unsafe_allow_html=True)
    for title, qq in reversed(st.session_state.history[-8:]):
        st.markdown(f"<div class='chip'>{title}</div><div class='small' style='margin:-6px 0 10px 0;'>{qq}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="hint">Можеш да питаш за административни процедури, закони, документи, услуги и компетентни институции в България.</div>', unsafe_allow_html=True)

q = st.chat_input("Напиши въпрос…")
if not q:
    st.stop()

# Save history immediately
st.session_state.history.append((make_title(q), q))
st.session_state.messages.append({"role": "user", "content": q})

intent = classify_intent(q)
follow = needs_clarification(q, intent)
sources = render_sources(q)

# Build context for AI (safe, no realtime claims)
context = f"Въпрос: {q}\n\n"
context += "Контекст: България, централна администрация. Дай практически стъпки.\n"
context += f"Разпозната тема: {intent}\n"
if follow:
    context += f"Нужна уточняваща информация: {follow}\n"
context += "\nОфициални държавни институции (релевантни за проверка):\n"
context += "\n".join([f"- {n}: {u}" for n, u in sources])

# Ask AI
with st.spinner("BGGovAI подготвя отговор…"):
    answer = ai_call(SYSTEM_PROMPT, context, get_model())

# Store assistant message
st.session_state.messages.append({"role": "assistant", "content": answer})

# Render last answer in structured UI
# We do lightweight parsing: first paragraphs -> summary; otherwise use as-is.
def split_summary(text: str) -> Tuple[str, str]:
    text = (text or "").strip()
    if not text:
        return ("(няма отговор)", "")
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], parts[1])

sum_part, rest_part = split_summary(answer)
ui_summary(sum_part)

if rest_part:
    ui_card("Подробности", rest_part.replace("\n", "<br>"))

if follow:
    ui_followup(f"👉 {follow}")

# Sources (only if toggle ON)
if check_sources:
    ui_sources(sources)

# Debug
if show_debug:
    st.session_state.last_debug = {
        "intent": intent,
        "followup": follow,
        "model": get_model(),
        "sources_count": len(sources),
    }
    ui_card("Технически детайли", f"<pre>{st.session_state.last_debug}</pre>")

# Render chat history (optional) – keep simple and stable
with st.expander("Покажи чат историята (сесия)", expanded=False):
    for m in st.session_state.messages[-20:]:
        role = "Ти" if m["role"] == "user" else "BGGovAI"
        ui_card(role, (m["content"] or "").replace("\n", "<br>"))
