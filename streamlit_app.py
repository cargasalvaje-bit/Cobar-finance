import os
import json
import time
import ssl
import certifi
import hashlib
import secrets
import hmac
import threading
from datetime import datetime, date

import pandas as pd
import streamlit as st
import finnhub
import websocket
from openai import OpenAI

# ============================================================
# COBAR — PERSONAL FINANCIAL INTELLIGENCE
# ============================================================

st.set_page_config(
    page_title="COBAR",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "META", "AMD", "GOOGL"]

# Store data beside this app.py, so accounts do not disappear when
# Streamlit is launched from a different working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "cobar_data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
os.makedirs(DATA_DIR, exist_ok=True)

FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")

# ============================================================
# DESIGN
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: #000000;
        color: #EAF2F0;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] {
        background: #020303;
        border-right: 1px solid #14201E;
    }

    [data-testid="stSidebar"] * {
        color: #DDE8E5 !important;
    }

    .cobar-logo {
        font-size: 44px;
        font-weight: 600;
        letter-spacing: 12px;
        color: #F0F7F5;
        margin-bottom: 3px;
    }

    .cobar-subtitle {
        font-size: 10px;
        letter-spacing: 4px;
        color: #16D98A;
        margin-bottom: 24px;
    }

    .eyebrow {
        color: #667C77;
        font-size: 10px;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .status-live {
        color: #16D98A;
        font-size: 12px;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    .status-warn {
        color: #E5B84B;
        font-size: 12px;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    .status-off {
        color: #FF5964;
        font-size: 12px;
        letter-spacing: 1.5px;
        font-weight: 600;
    }

    [data-testid="stMetric"] {
        background: #050908;
        border: 1px solid #17312B;
        border-radius: 12px;
        padding: 14px;
    }

    [data-testid="stMetricValue"] {
        color: #F2F8F6 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #758984 !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #050707 !important;
        color: #F0F6F4 !important;
        border: 1px solid #1A342E !important;
        border-radius: 9px !important;
    }

    .stSelectbox div[data-baseweb="select"] > div {
        background: #050707 !important;
        color: #F0F6F4 !important;
        border-color: #1A342E !important;
    }

    .stButton button {
        background: #06100D !important;
        color: #E6F0ED !important;
        border: 1px solid #1A4036 !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
    }

    .stButton button:hover {
        color: #16D98A !important;
        border-color: #16D98A !important;
        background: #071712 !important;
    }

    [data-testid="stChatMessage"] {
        background: #050807;
        border: 1px solid #142A25;
        border-radius: 12px;
    }

    [data-testid="stExpander"] {
        background: #030605;
        border: 1px solid #17312B;
        border-radius: 10px;
    }

    hr {
        border-color: #14201E !important;
    }

    a {
        color: #16D98A !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# LOCAL STORAGE
# ============================================================

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def normalize_username(username):
    return username.strip().lower()


def valid_username(username):
    import re
    return bool(re.fullmatch(r"[a-zA-Z0-9_-]{3,24}", username))


def user_file(username, kind):
    digest = hashlib.sha256(
        normalize_username(username).encode("utf-8")
    ).hexdigest()[:24]
    return os.path.join(DATA_DIR, f"{digest}_{kind}.json")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        300_000,
    ).hex()
    return salt, digest


def check_password(password, salt, stored_hash):
    _, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, stored_hash)


def create_account(username, password):
    username = normalize_username(username)
    users = load_json(USERS_FILE, {})

    if not valid_username(username):
        return False, "El usuario debe tener 3–24 caracteres y solo letras, números, _ o -."

    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    if username in users:
        return False, "Ese usuario ya existe."

    salt, password_hash = hash_password(password)
    users[username] = {
        "salt": salt,
        "password_hash": password_hash,
        "created": datetime.now().isoformat(),
    }
    save_json(USERS_FILE, users)

    save_json(user_file(username, "portfolio"), [])
    save_json(user_file(username, "notes"), [])
    save_json(user_file(username, "chat"), [])

    return True, "Cuenta creada."


def login(username, password):
    username = normalize_username(username)
    users = load_json(USERS_FILE, {})
    account = users.get(username)
    if not account:
        return False

    try:
        return check_password(
            password,
            account["salt"],
            account["password_hash"],
        )
    except (KeyError, TypeError):
        return False


# ============================================================
# LOGIN
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = None


def login_screen():
    st.markdown("<div style='height:70px'></div>", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])

    with center:
        st.markdown(
            '<div class="cobar-logo" style="text-align:center;">COBAR</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="cobar-subtitle" style="text-align:center;">PERSONAL FINANCIAL INTELLIGENCE</div>',
            unsafe_allow_html=True,
        )

        mode = st.radio(
            "ACCESS",
            ["Log in", "Create account"],
            horizontal=True,
        )

        username = st.text_input(
            "Username",
            placeholder="ej. Lorenzo",
        )
        password = st.text_input(
            "Password",
            type="password",
        )

        if mode == "Create account":
            confirm = st.text_input(
                "Confirm password",
                type="password",
            )

            if st.button(
                "CREATE ACCOUNT",
                use_container_width=True,
            ):
                if password != confirm:
                    st.error("Las contraseñas no coinciden.")
                else:
                    ok, message = create_account(
                        username,
                        password,
                    )
                    if ok:
                        st.success(
                            "Cuenta creada. Ahora inicia sesión."
                        )
                    else:
                        st.error(message)

        else:
            if st.button(
                "LOG IN",
                use_container_width=True,
            ):
                if login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = normalize_username(username)
                    st.rerun()
                else:
                    st.error(
                        "Usuario o contraseña incorrectos."
                    )

        st.caption(
            "Las cuentas y datos se guardan localmente en la carpeta "
            "cobar_data de este equipo."
        )


if not st.session_state.authenticated:
    login_screen()
    st.stop()


# ============================================================
# CURRENT USER DATA
# ============================================================

CURRENT_USER = st.session_state.username

PORTFOLIO_FILE = user_file(
    CURRENT_USER,
    "portfolio",
)
NOTES_FILE = user_file(
    CURRENT_USER,
    "notes",
)
CHAT_FILE = user_file(
    CURRENT_USER,
    "chat",
)

if st.session_state.get("loaded_user") != CURRENT_USER:
    st.session_state.portfolio = load_json(
        PORTFOLIO_FILE,
        [],
    )
    st.session_state.notes = load_json(
        NOTES_FILE,
        [],
    )
    st.session_state.chat = load_json(
        CHAT_FILE,
        [],
    )
    st.session_state.loaded_user = CURRENT_USER


# ============================================================
# FINNHUB REST
# ============================================================

@st.cache_resource
def create_finnhub(key):
    if not key:
        return None

    try:
        return finnhub.Client(api_key=key)
    except Exception:
        return None


fh = create_finnhub(FINNHUB_KEY)


@st.cache_data(ttl=2, show_spinner=False)
def get_quotes(symbols_tuple):
    if fh is None:
        return {}

    result = {}

    for symbol in symbols_tuple:
        try:
            result[symbol] = fh.quote(symbol)
        except Exception:
            result[symbol] = {}

    return result


@st.cache_data(ttl=30, show_spinner=False)
def get_chart(symbol):
    if fh is None:
        return None

    try:
        end = int(time.time())
        start = end - 86400

        data = fh.stock_candles(
            symbol,
            "5",
            start,
            end,
        )

        if data.get("s") != "ok":
            return None

        return pd.DataFrame(
            {
                "Time": pd.to_datetime(
                    data["t"],
                    unit="s",
                ),
                "Price": data["c"],
            }
        ).set_index("Time")

    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_news(symbol):
    if fh is None:
        return []

    try:
        today = datetime.now().strftime("%Y-%m-%d")

        news = fh.company_news(
            symbol,
            _from=today,
            to=today,
        )

        return news[:10]

    except Exception:
        return []


# ============================================================
# FINNHUB LIVE WEBSOCKET
# ============================================================

@st.cache_resource
def create_stream(key):
    prices = {}
    lock = threading.Lock()

    state = {
        "connected": False,
        "last_message": None,
        "error": None,
    }

    def on_open(ws):
        state["connected"] = True
        state["error"] = None

        for symbol in WATCHLIST:
            try:
                ws.send(
                    json.dumps(
                        {
                            "type": "subscribe",
                            "symbol": symbol,
                        }
                    )
                )
            except Exception:
                pass

    def on_message(ws, message):
        try:
            data = json.loads(message)

            if data.get("type") != "trade":
                return

            with lock:
                for trade in data.get("data", []):
                    symbol = trade.get("s")
                    price = trade.get("p")
                    timestamp = trade.get("t")

                    if (
                        symbol
                        and price is not None
                    ):
                        prices[symbol] = {
                            "price": float(price),
                            "timestamp": int(timestamp),
                        }

                        state["last_message"] = time.time()

        except Exception as exc:
            state["error"] = str(exc)

    def on_error(ws, error):
        state["connected"] = False
        state["error"] = str(error)

    def on_close(ws, code, msg):
        state["connected"] = False

    def run():
        while True:
            try:
                ws = websocket.WebSocketApp(
                    f"wss://ws.finnhub.io?token={key}",
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )

                ws.run_forever(
                    sslopt={
                        "cert_reqs": ssl.CERT_REQUIRED,
                        "ca_certs": certifi.where(),
                    },
                    ping_interval=20,
                    ping_timeout=10,
                )

            except Exception as exc:
                state["connected"] = False
                state["error"] = str(exc)

            time.sleep(5)

    if key:
        threading.Thread(
            target=run,
            daemon=True,
        ).start()

    return prices, lock, state


prices, price_lock, stream_state = create_stream(
    FINNHUB_KEY
)


def get_live_price(symbol):
    with price_lock:
        return prices.get(symbol)


# ============================================================
# OPENAI
# ============================================================

@st.cache_resource
def create_openai(key):
    if not key:
        return None

    try:
        return OpenAI(api_key=key)
    except Exception:
        return None


ai = create_openai(OPENAI_KEY)


def ask_cobar(
    question,
    context="",
):
    if ai is None:
        return (
            "COBAR AI está offline: falta OPENAI_API_KEY."
        )

    instructions = """
You are COBAR, a private personal financial intelligence assistant.
Speak Spanish unless another language is requested.

You analyze companies, technology, AI and financial markets.
You do not execute trades, connect to banks or brokers, or move money.
You never guarantee profits.

When discussing investments, give educational analysis,
assumptions, risks, scenarios and explain what information
could change the conclusion.

Clearly distinguish current market data from hypothetical analysis.
"""

    try:
        response = ai.responses.create(
            model="gpt-4.1",
            instructions=instructions,
            input=(
                "CURRENT MARKET DATA:\n"
                + context
                + "\n\nUSER:\n"
                + question
            ),
        )

        return response.output_text

    except Exception as exc:
        return f"COBAR AI ERROR: {exc}"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        '<div class="cobar-logo">COBAR</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">PERSONAL FINANCIAL INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### ACCOUNT")
    st.write(f"**{CURRENT_USER}**")

    page = st.radio(
        "SYSTEM",
        [
            "Command Center",
            "Market",
            "Investment AI",
            "Portfolio",
            "My Notes",
            "Intelligence Feed",
            "Media",
        ],
    )

    st.divider()

    if stream_state["connected"]:
        if (
            stream_state["last_message"]
            and time.time() - stream_state["last_message"] < 15
        ):
            st.markdown(
                '<div class="status-live">● FINNHUB LIVE STREAM</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="status-warn">● FINNHUB CONNECTED / WAITING</div>',
                unsafe_allow_html=True,
            )

    elif FINNHUB_KEY:
        st.markdown(
            '<div class="status-warn">● REST DATA ACTIVE</div>',
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            '<div class="status-off">● FINNHUB KEY MISSING</div>',
            unsafe_allow_html=True,
        )

    if OPENAI_KEY:
        st.markdown(
            '<div class="status-live">● COBAR AI KEY READY</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-off">● OPENAI KEY MISSING</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    if st.button(
        "LOG OUT",
        use_container_width=True,
    ):
        for key in [
            "portfolio",
            "notes",
            "chat",
            "loaded_user",
        ]:
            st.session_state.pop(
                key,
                None,
            )

        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()


# ============================================================
# MARKET HELPERS
# ============================================================

def quote_for(symbol):
    return get_quotes((symbol,)).get(
        symbol,
        {},
    )


def current_price(symbol):
    live = get_live_price(symbol)

    if live:
        return (
            live["price"],
            "LIVE STREAM",
        )

    quote = quote_for(symbol)

    if quote.get("c"):
        return (
            float(quote["c"]),
            "REST",
        )

    return None, "NO DATA"


def render_stock(symbol):
    price, source = current_price(symbol)
    quote = quote_for(symbol)

    if price is None:
        st.metric(
            symbol,
            "N/D",
            "NO DATA",
        )
        return

    previous = quote.get("pc")

    if previous:
        pct = (
            (price - previous)
            / previous
            * 100
        )
    else:
        pct = quote.get(
            "dp",
            0,
        )

    st.metric(
        symbol,
        f"${price:,.2f}",
        f"{pct:+.2f}%",
    )

    if source == "LIVE STREAM":
        st.caption("● LIVE")
    else:
        st.caption("● REST · refreshed ~2s")


def connection_banner():
    connected = stream_state["connected"]
    last = stream_state["last_message"]

    if (
        connected
        and last
        and time.time() - last < 15
    ):
        text = "● LIVE MARKET STREAM"
        cls = "status-live"

    elif connected:
        text = "● CONNECTED / WAITING FOR TICKS"
        cls = "status-warn"

    elif FINNHUB_KEY:
        text = "● STREAM OFFLINE · REST DATA ACTIVE"
        cls = "status-warn"

    else:
        text = "● FINNHUB KEY MISSING"
        cls = "status-off"

    st.markdown(
        '<div class="eyebrow">MARKET CONNECTION</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{cls}">{text}</div>',
        unsafe_allow_html=True,
    )


def market_overview():
    connection_banner()

    cols = st.columns(4)

    for col, symbol in zip(
        cols,
        WATCHLIST[:4],
    ):
        with col:
            render_stock(symbol)

    cols = st.columns(4)

    for col, symbol in zip(
        cols,
        WATCHLIST[4:],
    ):
        with col:
            render_stock(symbol)


# ============================================================
# COMMAND CENTER
# ============================================================

def command_center():
    st.markdown(
        '<div class="cobar-logo">COBAR</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">PERSONAL FINANCIAL INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )

    market_overview()

    st.divider()

    st.markdown("### 📡 MARKET NEWS")

    symbol = st.selectbox(
        "Company",
        WATCHLIST,
        key="command_news",
    )

    news = get_news(symbol)

    if news:
        for item in news:
            title = item.get(
                "headline",
                "Untitled",
            )

            source = item.get(
                "source",
                "Unknown",
            )

            st.markdown(f"**{title}**")
            st.caption(source)
            st.divider()

    else:
        st.info(
            "No hay noticias disponibles para hoy."
        )

    st.markdown("### ◈ COBAR AI")

    for message in st.session_state.chat:
        with st.chat_message(
            message["role"]
        ):
            st.write(
                message["content"]
            )

    prompt = st.chat_input(
        "Ask COBAR about a company, market or idea..."
    )

    if prompt:
        st.session_state.chat.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        save_json(
            CHAT_FILE,
            st.session_state.chat,
        )

        context_lines = []

        for ticker in WATCHLIST:
            price, source = current_price(
                ticker
            )

            if price is not None:
                context_lines.append(
                    f"{ticker}: ${price:.2f} ({source})"
                )

        answer = ask_cobar(
            prompt,
            "\n".join(context_lines),
        )

        st.session_state.chat.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        save_json(
            CHAT_FILE,
            st.session_state.chat,
        )

        st.rerun()


# ============================================================
# MARKET
# ============================================================

def market_page():
    st.markdown(
        '<div class="cobar-logo">MARKET</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">LIVE MARKET INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )

    market_overview()

    st.divider()

    symbol = st.selectbox(
        "SYMBOL",
        WATCHLIST,
        key="market_symbol",
    )

    price, source = current_price(symbol)

    if price is not None:
        st.metric(
            "CURRENT PRICE",
            f"${price:,.2f}",
        )
        st.caption(source)

    chart = get_chart(symbol)

    if chart is not None:
        st.line_chart(
            chart["Price"],
            height=450,
        )
    else:
        st.info(
            "No hay datos históricos disponibles."
        )


# ============================================================
# INVESTMENT AI
# ============================================================

def investment_ai_page():
    st.markdown(
        '<div class="cobar-logo">INVESTMENT AI</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">EDUCATIONAL MARKET ANALYSIS</div>',
        unsafe_allow_html=True,
    )

    st.info(
        "COBAR ayuda a analizar escenarios. "
        "No ejecuta operaciones ni mueve dinero."
    )

    capital = st.number_input(
        "Capital hipotético",
        min_value=0.0,
        value=1000.0,
        step=100.0,
    )

    horizon = st.selectbox(
        "Horizonte",
        [
            "Corto plazo",
            "Mediano plazo",
            "Largo plazo",
        ],
    )

    objective = st.selectbox(
        "Objetivo",
        [
            "Aprender",
            "Crecimiento",
            "Diversificación",
            "Entender riesgo",
        ],
    )

    details = st.text_area(
        "¿Qué quieres analizar?",
        placeholder="Ej. comparar NVDA y AMD...",
    )

    if st.button(
        "ANALIZAR ESCENARIO",
        use_container_width=True,
    ):
        prompt = f"""
Analiza educativamente este escenario.

Capital hipotético: ${capital:,.2f}
Horizonte: {horizon}
Objetivo: {objective}
Solicitud: {details}

Usa la información de mercado disponible en el contexto.

Explica:
1. Datos que habría que revisar.
2. Factores de la empresa/mercado.
3. Riesgos.
4. Escenario favorable.
5. Escenario desfavorable.
6. Qué información podría cambiar la conclusión.

No prometas ganancias y no ejecutes operaciones.
"""

        context_lines = []

        for ticker in WATCHLIST:
            price, _ = current_price(ticker)

            if price is not None:
                context_lines.append(
                    f"{ticker}: ${price:.2f}"
                )

        st.write(
            ask_cobar(
                prompt,
                "\n".join(context_lines),
            )
        )


# ============================================================
# PORTFOLIO
# ============================================================

def portfolio_page():
    st.markdown(
        '<div class="cobar-logo">PORTFOLIO</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">PERSONAL INVESTMENT HISTORY</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        f"Portfolio de {CURRENT_USER}. "
        "No está conectado a ningún broker."
    )

    with st.expander(
        "⚙ PORTFOLIO SETTINGS"
    ):
        st.warning(
            "RESET PORTFOLIO elimina todas las inversiones "
            "registradas de esta cuenta."
        )

        if st.button(
            "RESET PORTFOLIO",
            use_container_width=True,
        ):
            st.session_state.portfolio = []

            save_json(
                PORTFOLIO_FILE,
                [],
            )

            st.success(
                "Portfolio reseteado."
            )

            st.rerun()

    st.divider()

    with st.form(
        "trade_form",
        clear_on_submit=True,
    ):
        c1, c2 = st.columns(2)

        with c1:
            symbol = st.text_input(
                "Ticker",
                placeholder="NVDA",
            ).upper().strip()

            shares = st.number_input(
                "Cantidad",
                min_value=0.0001,
                value=1.0,
                step=1.0,
            )

        with c2:
            entry = st.number_input(
                "Precio de entrada",
                min_value=0.01,
                value=100.0,
                step=1.0,
            )

            trade_date = st.date_input(
                "Fecha",
                value=date.today(),
            )

        submitted = st.form_submit_button(
            "GUARDAR INVERSIÓN",
            use_container_width=True,
        )

    if submitted:
        if not symbol:
            st.error(
                "Introduce un ticker."
            )
        else:
            st.session_state.portfolio.append(
                {
                    "symbol": symbol,
                    "shares": float(shares),
                    "entry": float(entry),
                    "date": str(trade_date),
                }
            )

            save_json(
                PORTFOLIO_FILE,
                st.session_state.portfolio,
            )

            st.success(
                "Inversión registrada."
            )

            st.rerun()

    total_cost = 0.0
    total_value = 0.0

    if not st.session_state.portfolio:
        st.info(
            "Este portfolio está vacío."
        )

    for index, trade in enumerate(
        st.session_state.portfolio
    ):
        symbol = trade["symbol"]
        price, source = current_price(
            symbol
        )

        invested = (
            float(trade["shares"])
            * float(trade["entry"])
        )

        total_cost += invested

        with st.container(border=True):
            st.subheader(symbol)

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Entrada",
                f"${trade['entry']:,.2f}",
            )

            c2.metric(
                "Cantidad",
                f"{trade['shares']:g}",
            )

            if price is not None:
                value = (
                    float(trade["shares"])
                    * price
                )

                pnl = value - invested

                pct = (
                    pnl / invested * 100
                    if invested
                    else 0
                )

                total_value += value

                c3.metric(
                    "Actual",
                    f"${price:,.2f}",
                )

                c4.metric(
                    "P/L",
                    f"${pnl:+,.2f}",
                    f"{pct:+.2f}%",
                )

                st.caption(
                    f"{trade['date']} · {source}"
                )

            else:
                c3.metric(
                    "Actual",
                    "N/D",
                )

                c4.metric(
                    "P/L",
                    "N/D",
                )

                st.caption(
                    f"{trade['date']} · precio no disponible"
                )

            if st.button(
                "ELIMINAR",
                key=f"delete_trade_{index}",
            ):
                st.session_state.portfolio.pop(
                    index
                )

                save_json(
                    PORTFOLIO_FILE,
                    st.session_state.portfolio,
                )

                st.rerun()

    if total_cost:
        st.divider()

        total_pnl = (
            total_value
            - total_cost
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "TOTAL INVERTIDO",
            f"${total_cost:,.2f}",
        )

        c2.metric(
            "VALOR ACTUAL",
            f"${total_value:,.2f}",
        )

        c3.metric(
            "P/L TOTAL",
            f"${total_pnl:+,.2f}",
        )


# ============================================================
# MY NOTES
# ============================================================

def notes_page():
    st.markdown(
        '<div class="cobar-logo">MY NOTES</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">PRIVATE KNOWLEDGE</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        f"Notas privadas de {CURRENT_USER}. "
        "Solo esta cuenta puede editarlas."
    )

    with st.form(
        "note_form",
        clear_on_submit=True,
    ):
        title = st.text_input(
            "Título"
        )

        content = st.text_area(
            "Nota",
            height=150,
        )

        save = st.form_submit_button(
            "GUARDAR NOTA",
            use_container_width=True,
        )

    if save:
        if (
            not title.strip()
            or not content.strip()
        ):
            st.error(
                "Completa título y nota."
            )

        else:
            st.session_state.notes.append(
                {
                    "title": title.strip(),
                    "content": content.strip(),
                    "date": datetime.now().strftime(
                        "%d/%m/%Y %H:%M"
                    ),
                }
            )

            save_json(
                NOTES_FILE,
                st.session_state.notes,
            )

            st.success(
                "Nota guardada."
            )

            st.rerun()

    st.divider()

    for index in range(
        len(st.session_state.notes) - 1,
        -1,
        -1,
    ):
        note = st.session_state.notes[index]

        with st.container(border=True):
            st.subheader(
                note["title"]
            )

            st.caption(
                note["date"]
            )

            st.write(
                note["content"]
            )

            if st.button(
                "ELIMINAR NOTA",
                key=f"delete_note_{index}",
            ):
                st.session_state.notes.pop(
                    index
                )

                save_json(
                    NOTES_FILE,
                    st.session_state.notes,
                )

                st.rerun()


# ============================================================
# INTELLIGENCE FEED
# ============================================================

def intelligence_feed_page():
    st.markdown(
        '<div class="cobar-logo">INTELLIGENCE FEED</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">COMPANY NEWS</div>',
        unsafe_allow_html=True,
    )

    symbol = st.selectbox(
        "Empresa",
        WATCHLIST,
        key="feed_symbol",
    )

    news = get_news(symbol)

    if not news:
        st.info(
            "No hay noticias disponibles para hoy."
        )
        return

    for item in news:
        headline = item.get(
            "headline",
            "Sin título",
        )

        source = item.get(
            "source",
            "Unknown",
        )

        url = item.get("url")

        st.markdown(
            f"**{headline}**"
        )

        st.caption(source)

        if url:
            st.link_button(
                "OPEN SOURCE",
                url,
            )

        st.divider()


# ============================================================
# MEDIA
# ============================================================

def media_page():
    st.markdown(
        '<div class="cobar-logo">MEDIA</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cobar-subtitle">VIDEO INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "Pega una URL de YouTube de una entrevista "
        "o conversación que quieras ver."
    )

    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
    )

    if url:
        if (
            "youtube.com" in url
            or "youtu.be" in url
        ):
            st.video(url)
        else:
            st.error(
                "Introduce una URL de YouTube válida."
            )


# ============================================================
# AUTO REFRESH — 2 SECONDS
# ============================================================

# Streamlit's fragment refreshes the visible page every 2 seconds
# without restarting the whole app. This keeps REST fallback prices
# and the live stream status moving.
try:
    fragment = st.fragment
except AttributeError:
    fragment = None


if fragment is not None:

    @fragment(run_every=2)
    def live_area():
        if page == "Command Center":
            command_center()

        elif page == "Market":
            market_page()

        elif page == "Investment AI":
            investment_ai_page()

        elif page == "Portfolio":
            portfolio_page()

        elif page == "My Notes":
            notes_page()

        elif page == "Intelligence Feed":
            intelligence_feed_page()

        elif page == "Media":
            media_page()

    live_area()

else:
    if page == "Command Center":
        command_center()

    elif page == "Market":
        market_page()

    elif page == "Investment AI":
        investment_ai_page()

    elif page == "Portfolio":
        portfolio_page()

    elif page == "My Notes":
        notes_page()

    elif page == "Intelligence Feed":
        intelligence_feed_page()

    elif page == "Media":
        media_page()


