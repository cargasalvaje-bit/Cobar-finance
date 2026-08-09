python
import streamlit as st
import finnhub
import websocket
import threading
import json
import time
import ssl
import certifi
import pandas as pd
import os
import hashlib
import secrets
import hmac
import re
from datetime import datetime
from openai import OpenAI


# =========================================================
# COBAR
# PERSONAL FINANCIAL INTELLIGENCE
# =========================================================

st.set_page_config(
    page_title="COBAR",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# CONFIG
# =========================================================

WATCHLIST = [
    "NVDA",
    "TSLA",
    "AAPL",
    "MSFT",
    "AMZN",
    "META",
    "AMD",
    "GOOGL"
]

DATA_DIR = "cobar_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

os.makedirs(DATA_DIR, exist_ok=True)

FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")


# =========================================================
# PREMIUM TERMINAL DESIGN
# =========================================================

st.markdown(
    """
    <style>

    /* =========================
       GLOBAL
       ========================= */

    .stApp {
        background:
            radial-gradient(
                circle at 50% -20%,
                #071310 0%,
                #020505 35%,
                #000000 70%
            );
        color: #E8EEEE;
    }

    .main .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* =========================
       SIDEBAR
       ========================= */

    [data-testid="stSidebar"] {
        background: #020404;
        border-right: 1px solid #10211E;
    }

    [data-testid="stSidebar"] * {
        color: #DDE7E4 !important;
    }

    [data-testid="stSidebar"] .stRadio label:hover {
        color: #16D98A !important;
    }

    /* =========================
       TEXT
       ========================= */

    .cobar-logo {
        font-size: 42px;
        font-weight: 600;
        letter-spacing: 11px;
        color: #E8EEEE;
        margin-bottom: 2px;
    }

    .cobar-subtitle {
        color: #16D98A;
        font-size: 9px;
        letter-spacing: 3px;
        font-weight: 600;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 11px;
        letter-spacing: 3px;
        color: #71817D;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 12px;
    }

    .terminal-title {
        font-size: 34px;
        letter-spacing: 8px;
        font-weight: 500;
        color: #F0F5F3;
        margin-bottom: 3px;
    }

    .terminal-subtitle {
        color: #16D98A;
        font-size: 10px;
        letter-spacing: 4px;
        font-weight: 600;
        margin-bottom: 28px;
    }

    .muted {
        color: #64736F;
        font-size: 11px;
    }

    /* =========================
       PANELS
       ========================= */

    .terminal-panel {
        background:
            linear-gradient(
                145deg,
                #07100E,
                #030706
            );
        border: 1px solid #112A24;
        border-radius: 10px;
        padding: 20px;
        box-shadow:
            0 8px 30px rgba(0,0,0,0.35);
        margin-bottom: 14px;
    }

    .metric-panel {
        background:
            linear-gradient(
                145deg,
                #07110E,
                #030706
            );
        border: 1px solid #123128;
        border-radius: 10px;
        padding: 18px 20px;
        min-height: 145px;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.02),
            0 8px 25px rgba(0,0,0,0.25);
    }

    .metric-symbol {
        color: #6E817B;
        font-size: 10px;
        letter-spacing: 3px;
        font-weight: 700;
    }

    .metric-price {
        color: #F0F5F3;
        font-size: 29px;
        font-weight: 500;
        margin-top: 9px;
        margin-bottom: 5px;
    }

    .metric-positive {
        color: #16D98A;
        font-size: 13px;
        font-weight: 700;
    }

    .metric-negative {
        color: #16D98A;
        font-size: 13px;
        font-weight: 700;
    }

    .metric-status {
        color: #60716C;
        font-size: 9px;
        letter-spacing: 2px;
        margin-top: 12px;
    }

    /* =========================
       CONNECTION
       ========================= */

    .connection-live {
        background: #04110D;
        border: 1px solid #123D2E;
        border-radius: 8px;
        padding: 13px 16px;
        margin-bottom: 18px;
    }

    .connection-wait {
        background: #080B08;
        border: 1px solid #263127;
        border-radius: 8px;
        padding: 13px 16px;
        margin-bottom: 18px;
    }

    .connection-offline {
        background: #090505;
        border: 1px solid #291111;
        border-radius: 8px;
        padding: 13px 16px;
        margin-bottom: 18px;
    }

    .live-dot {
        color: #16D98A;
        font-weight: 700;
    }

    .wait-dot {
        color: #A4B09F;
        font-weight: 700;
    }

    .offline-dot {
        color: #16D98A;
        font-weight: 700;
    }

    /* =========================
       NEWS
       ========================= */

    .news-card {
        background: #030706;
        border: 1px solid #10231F;
        border-radius: 8px;
        padding: 17px 19px;
        margin-bottom: 9px;
        transition: 0.2s;
    }

    .news-card:hover {
        border-color: #16D98A;
        background: #05100C;
    }

    .news-headline {
        color: #E3ECE9;
        font-size: 14px;
        line-height: 1.45;
        font-weight: 500;
    }

    .news-source {
        color: #52635E;
        font-size: 9px;
        letter-spacing: 2px;
        margin-top: 9px;
    }

    /* =========================
       ACCOUNT
       ========================= */

    .account-box {
        background: #050908;
        border: 1px solid #122B25;
        border-radius: 8px;
        padding: 12px 14px;
        margin: 12px 0 16px;
    }

    .account-label {
        color: #53635F;
        font-size: 8px;
        letter-spacing: 2px;
    }

    .account-name {
        color: #E5ECEA;
        font-size: 14px;
        font-weight: 600;
    }

    /* =========================
       AI CHAT
       ========================= */

    .ai-header {
        background:
            linear-gradient(
                90deg,
                #06100D,
                #030706
            );
        border: 1px solid #123128;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 15px;
    }

    .ai-name {
        color: #EAF1EF;
        font-size: 17px;
        letter-spacing: 3px;
        font-weight: 600;
    }

    .ai-status {
        color: #16D98A;
        font-size: 9px;
        letter-spacing: 2px;
        margin-top: 4px;
    }

    /* =========================
       PORTFOLIO
       ========================= */

    .portfolio-card {
        background: #030706;
        border: 1px solid #112A24;
        border-radius: 9px;
        padding: 19px;
        margin-bottom: 10px;
    }

    .portfolio-symbol {
        color: #F0F5F3;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 2px;
    }

    .portfolio-data {
        color: #687873;
        font-size: 10px;
        letter-spacing: 1px;
    }

    .portfolio-value {
        color: #E6EEEB;
        font-size: 17px;
        font-weight: 500;
    }

    /* =========================
       NOTES
       ========================= */

    .note-card {
        background: #030706;
        border: 1px solid #112A24;
        border-radius: 9px;
        padding: 18px;
        margin-bottom: 10px;
    }

    .note-title {
        color: #E5ECEA;
        font-size: 16px;
        font-weight: 600;
    }

    .note-date {
        color: #53635E;
        font-size: 9px;
        letter-spacing: 2px;
    }

    .note-content {
        color: #B9C4C0;
        font-size: 13px;
        line-height: 1.6;
        margin-top: 12px;
    }

    /* =========================
       STREAMLIT CONTROLS
       ========================= */

    .stButton button {
        background: #050908 !important;
        color: #DDE7E4 !important;
        border: 1px solid #17332C !important;
        border-radius: 7px !important;
        min-height: 40px;
        font-weight: 600;
        letter-spacing: 1px;
    }

    .stButton button:hover {
        color: #16D98A !important;
        border-color: #16D98A !important;
        background: #06100C !important;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #030706 !important;
        color: #E8EEEE !important;
        border: 1px solid #17332C !important;
        border-radius: 7px !important;
    }

    .stSelectbox div[data-baseweb="select"] > div {
        background: #030706 !important;
        border-color: #17332C !important;
    }

    .stDateInput input {
        background: #030706 !important;
        color: #E8EEEE !important;
        border-color: #17332C !important;
    }

    div[data-testid="stMetric"] {
        background: #030706;
        border: 1px solid #112A24;
        border-radius: 8px;
        padding: 15px;
    }

    div[data-testid="stMetricLabel"] {
        color: #65756F !important;
    }

    div[data-testid="stMetricValue"] {
        color: #E8EEEE !important;
    }

    hr {
        border-color: #10231F !important;
    }

    /* =========================
       CHAT
       ========================= */

    [data-testid="stChatMessage"] {
        background: #030706;
        border: 1px solid #10231F;
        border-radius: 9px;
        margin-bottom: 8px;
    }

    /* =========================
       LOGIN
       ========================= */

    .login-container {
        max-width: 480px;
        margin: 100px auto;
    }

    .login-card {
        background:
            linear-gradient(
                145deg,
                #07100E,
                #020504
            );
        border: 1px solid #16342C;
        border-radius: 12px;
        padding: 42px;
        box-shadow:
            0 20px 70px rgba(0,0,0,0.55);
    }

    .login-logo {
        text-align: center;
        font-size: 48px;
        letter-spacing: 13px;
        color: #EAF1EF;
    }

    .login-sub {
        text-align: center;
        color: #16D98A;
        font-size: 9px;
        letter-spacing: 4px;
        margin-bottom: 35px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SECURITY / USERS
# =========================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(filename, data):
    directory = os.path.dirname(filename)

    os.makedirs(
        directory if directory else ".",
        exist_ok=True
    )

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def normalize_username(username):
    return username.strip().lower()


def valid_username(username):
    return bool(
        re.fullmatch(
            r"[a-zA-Z0-9_-]{3,24}",
            username
        )
    )


def user_file(username, kind):
    safe = hashlib.sha256(
        normalize_username(username).encode()
    ).hexdigest()[:24]

    return os.path.join(
        DATA_DIR,
        f"{safe}_{kind}.json"
    )


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return salt, password_hash


def check_password(password, salt, stored_hash):
    _, calculated = hash_password(
        password,
        salt
    )

    return hmac.compare_digest(
        calculated,
        stored_hash
    )


def create_account(username, password):
    username = normalize_username(username)

    users = load_json(
        USERS_FILE,
        {}
    )

    if username in users:
        return False, "Ese usuario ya existe."

    if not valid_username(username):
        return False, (
            "El usuario debe tener entre 3 y 24 "
            "caracteres y solo usar letras, números, "
            "_ o -."
        )

    if len(password) < 6:
        return False, (
            "La contraseña debe tener al menos "
            "6 caracteres."
        )

    salt, password_hash = hash_password(
        password
    )

    users[username] = {
        "salt": salt,
        "password_hash": password_hash,
        "created": datetime.now().isoformat()
    }

    save_json(
        USERS_FILE,
        users
    )

    save_json(
        user_file(username, "portfolio"),
        []
    )

    save_json(
        user_file(username, "notes"),
        []
    )

    save_json(
        user_file(username, "chat"),
        []
    )

    return True, "Cuenta creada."


def login(username, password):
    username = normalize_username(username)

    users = load_json(
        USERS_FILE,
        {}
    )

    if username not in users:
        return False

    account = users[username]

    return check_password(
        password,
        account["salt"],
        account["password_hash"]
    )


# =========================================================
# SESSION
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "username" not in st.session_state:
    st.session_state.username = None


# =========================================================
# LOGIN SCREEN
# =========================================================

def login_screen():

    st.markdown(
        """
        <div class="login-container">
            <div class="login-card">
                <div class="login-logo">COBAR</div>
                <div class="login-sub">
                    PERSONAL FINANCIAL INTELLIGENCE
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    mode = st.radio(
        "ACCESS",
        ["Log in", "Create account"],
        horizontal=True
    )

    username = st.text_input(
        "Username",
        placeholder="ej. Lorenzo"
    )

    password = st.text_input(
        "Password",
        type="password"
    )

    if mode == "Create account":

        confirm = st.text_input(
            "Confirm password",
            type="password"
        )

        if st.button(
            "CREATE ACCOUNT",
            use_container_width=True
        ):

            if password != confirm:

                st.error(
                    "Las contraseñas no coinciden."
                )

            else:

                success, message = create_account(
                    username,
                    password
                )

                if success:
                    st.success(
                        "Cuenta creada. Ahora puedes iniciar sesión."
                    )
                else:
                    st.error(message)

    else:

        if st.button(
            "LOG IN",
            use_container_width=True
        ):

            if login(
                username,
                password
            ):

                st.session_state.authenticated = True
                st.session_state.username = (
                    normalize_username(username)
                )

                st.rerun()

            else:

                st.error(
                    "Usuario o contraseña incorrectos."
                )


if not st.session_state.authenticated:
    login_screen()
    st.stop()


# =========================================================
# CURRENT USER DATA
# =========================================================

CURRENT_USER = st.session_state.username

PORTFOLIO_FILE = user_file(
    CURRENT_USER,
    "portfolio"
)

NOTES_FILE = user_file(
    CURRENT_USER,
    "notes"
)

CHAT_FILE = user_file(
    CURRENT_USER,
    "chat"
)


if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_json(
        PORTFOLIO_FILE,
        []
    )


if "notes" not in st.session_state:
    st.session_state.notes = load_json(
        NOTES_FILE,
        []
    )


if "chat" not in st.session_state:
    st.session_state.chat = load_json(
        CHAT_FILE,
        []
    )


# =========================================================
# FINNHUB
# =========================================================

@st.cache_resource
def create_finnhub(key):

    if not key:
        return None

    try:
        return finnhub.Client(
            api_key=key
        )
    except Exception:
        return None


fh = create_finnhub(FINNHUB_KEY)


@st.cache_data(ttl=5)
def get_quotes(symbols):

    if fh is None:
        return {}

    result = {}

    for symbol in symbols:

        try:
            result[symbol] = fh.quote(
                symbol
            )
        except Exception:
            result[symbol] = {}

    return result


@st.cache_data(ttl=60)
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
            end
        )

        if data.get("s") != "ok":
            return None

        df = pd.DataFrame({
            "Time": pd.to_datetime(
                data["t"],
                unit="s"
            ),
            "Price": data["c"]
        })

        return df.set_index("Time")

    except Exception:
        return None


@st.cache_data(ttl=60)
def get_news(symbol):

    if fh is None:
        return []

    try:

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        return fh.company_news(
            symbol,
            _from=today,
            to=today
        )[:10]

    except Exception:
        return []


# =========================================================
# WEBSOCKET
# =========================================================

@st.cache_resource
def create_stream(key):

    prices = {}
    lock = threading.Lock()

    state = {
        "connected": False,
        "last_message": None,
        "error": None
    }

    def on_open(ws):

        state["connected"] = True
        state["error"] = None

        for symbol in WATCHLIST:

            ws.send(
                json.dumps({
                    "type": "subscribe",
                    "symbol": symbol
                })
            )

    def on_message(ws, message):

        try:

            data = json.loads(message)

            if data.get("type") != "trade":
                return

            with lock:

                for trade in data.get(
                    "data",
                    []
                ):

                    symbol = trade.get("s")
                    price = trade.get("p")
                    timestamp = trade.get("t")

                    if symbol and price:

                        prices[symbol] = {
                            "price": float(price),
                            "timestamp": int(timestamp)
                        }

                        state["last_message"] = time.time()

        except Exception as e:

            state["error"] = str(e)

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
                    on_close=on_close
                )

                ws.run_forever(
                    sslopt={
                        "cert_reqs": ssl.CERT_REQUIRED,
                        "ca_certs": certifi.where()
                    },
                    ping_interval=20,
                    ping_timeout=10
                )

            except Exception as e:

                state["connected"] = False
                state["error"] = str(e)

            time.sleep(5)

    if key:

        thread = threading.Thread(
            target=run,
            daemon=True
        )

        thread.start()

    return prices, lock, state


prices, price_lock, stream_state = create_stream(
    FINNHUB_KEY
)


def get_live_price(symbol):

    with price_lock:
        return prices.get(symbol)


# =========================================================
# OPENAI
# =========================================================

@st.cache_resource
def create_openai(key):

    if not key:
        return None

    try:
        return OpenAI(
            api_key=key
        )
    except Exception:
        return None


ai = create_openai(
    OPENAI_KEY
)


def ask_cobar(
    question,
    context=""
):

    if ai is None:

        return (
            "COBAR AI está offline. "
            "Revisa OPENAI_API_KEY."
        )

    instructions = """
You are COBAR, a private personal intelligence assistant.

Speak Spanish unless another language is requested.

You analyze companies, technology, AI and financial markets.

You NEVER execute trades.
You NEVER connect to a bank or broker.
You NEVER move money.
You NEVER guarantee profits.

When discussing investments, provide educational
analysis, risks, assumptions and scenarios.

Clearly distinguish current data from hypothetical analysis.
"""

    try:

        response = ai.responses.create(
            model="gpt-5",
            instructions=instructions,
            input=(
                "CURRENT MARKET DATA:\n"
                + context
                + "\n\nUSER:\n"
                + question
            )
        )

        return response.output_text

    except Exception as e:

        return f"COBAR AI ERROR: {e}"


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        '<div class="cobar-logo">COBAR</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="cobar-subtitle">'
        'PERSONAL FINANCIAL INTELLIGENCE'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
        f"""
        <div class="account-box">
            <div class="account-label">
                LOGGED IN AS
            </div>
            <div class="account-name">
                {CURRENT_USER}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    page = st.radio(
        "SYSTEM",
        [
            "Command Center",
            "Market",
            "Investment AI",
            "Portfolio",
            "My Notes",
            "Intelligence Feed",
            "Media"
        ]
    )

    st.divider()

    if FINNHUB_KEY:

        st.markdown(
            '<span class="live-dot">● FINNHUB API</span>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<span class="offline-dot">'
            '● FINNHUB KEY MISSING'
            '</span>',
            unsafe_allow_html=True
        )

    if OPENAI_KEY:

        st.markdown(
            '<span class="live-dot">● COBAR AI</span>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<span class="offline-dot">'
            '● OPENAI KEY MISSING'
            '</span>',
            unsafe_allow_html=True
        )

    st.divider()

    if st.button(
        "LOG OUT",
        use_container_width=True
    ):

        st.session_state.authenticated = False
        st.session_state.username = None

        for key in [
            "portfolio",
            "notes",
            "chat"
        ]:
            st.session_state.pop(
                key,
                None
            )

        st.rerun()


# =========================================================
# CONNECTION STATUS
# =========================================================

def render_connection():

    connected = stream_state["connected"]
    last_message = stream_state["last_message"]

    if connected and last_message:

        age = time.time() - last_message

        if age < 15:

            st.markdown(
                """
                <div class="connection-live">
                    <span class="live-dot">
                        ● LIVE MARKET STREAM
                    </span>
                    &nbsp;&nbsp;
                    <span class="muted">
                        Finnhub WebSocket
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                """
                <div class="connection-wait">
                    <span class="wait-dot">
                        ● CONNECTED / WAITING
                    </span>
                    &nbsp;&nbsp;
                    <span class="muted">
                        Waiting for market ticks
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

    elif connected:

        st.markdown(
            """
            <div class="connection-wait">
                <span class="wait-dot">
                    ● CONNECTED / WAITING
                </span>
                &nbsp;&nbsp;
                <span class="muted">
                    Waiting for market ticks
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="connection-offline">
                <span class="offline-dot">
                    ● STREAM OFFLINE
                </span>
                &nbsp;&nbsp;
                <span class="muted">
                    REST market data may still be available
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# STOCK CARD
# =========================================================

def render_stock_card(symbol):

    live = get_live_price(symbol)

    quote = get_quotes(
        [symbol]
    ).get(
        symbol,
        {}
    )

    if live:

        price = live["price"]

        previous = quote.get("pc")

        if previous:
            pct = (
                (price - previous)
                / previous
                * 100
            )
        else:
            pct = 0

        timestamp = datetime.fromtimestamp(
            live["timestamp"] / 1000
        ).strftime("%H:%M:%S")

        st.markdown(
            f"""
            <div class="metric-panel">

                <div class="metric-symbol">
                    {symbol}
                </div>

                <div class="metric-price">
                    ${price:,.2f}
                </div>

                <div class="metric-positive">
                    {pct:+.2f}%
                </div>

                <div class="metric-status">
                    ● LIVE · {timestamp}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    elif quote.get("c"):

        price = quote["c"]
        pct = quote.get("dp", 0)

        st.markdown(
            f"""
            <div class="metric-panel">

                <div class="metric-symbol">
                    {symbol}
                </div>

                <div class="metric-price">
                    ${price:,.2f}
                </div>

                <div class="metric-positive">
                    {pct:+.2f}%
                </div>

                <div class="metric-status">
                    REST MARKET DATA
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            f"""
            <div class="metric-panel">

                <div class="metric-symbol">
                    {symbol}
                </div>

                <div class="metric-price">
                    N/D
                </div>

                <div class="metric-status">
                    DATA UNAVAILABLE
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# MARKET DASHBOARD
# =========================================================

def market_dashboard():

    render_connection()

    cols = st.columns(4)

    for col, symbol in zip(
        cols,
        [
            "NVDA",
            "TSLA",
            "AAPL",
            "MSFT"
        ]
    ):

        with col:
            render_stock_card(symbol)

    st.markdown(
        '<div class="section-title">'
        'LIVE MARKET CHART'
        '</div>',
        unsafe_allow_html=True
    )

    selected = st.selectbox(
        "SYMBOL",
        WATCHLIST,
        key="dashboard_symbol"
    )

    live = get_live_price(selected)

    quote = get_quotes(
        [selected]
    ).get(
        selected,
        {}
    )

    if live:

        st.metric(
            "LIVE PRICE",
            f"${live['price']:,.2f}"
        )

    elif quote.get("c"):

        st.metric(
            "PRICE",
            f"${quote['c']:,.2f}"
        )

    chart = get_chart(selected)

    if chart is not None:

        st.line_chart(
            chart["Price"],
            height=400
        )

    else:

        st.info(
            "No hay datos históricos disponibles."
        )


# =========================================================
# COMMAND CENTER
# =========================================================

if page == "Command Center":

    st.markdown(
        '<div class="terminal-title">COBAR</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'PERSONAL FINANCIAL INTELLIGENCE'
        '</div>',
        unsafe_allow_html=True
    )

    market_dashboard()

    st.divider()

    st.markdown(
        '<div class="section-title">'
        'MARKET NEWS'
        '</div>',
        unsafe_allow_html=True
    )

    news_symbol = st.selectbox(
        "COMPANY",
        WATCHLIST,
        key="command_news"
    )

    news = get_news(news_symbol)

    if news:

        for item in news:

            headline = item.get(
                "headline",
                "Untitled"
            )

            source = item.get(
                "source",
                ""
            )

            st.markdown(
                f"""
                <div class="news-card">

                    <div class="news-headline">
                        {headline}
                    </div>

                    <div class="news-source">
                        {source}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "No hay noticias disponibles."
        )

    st.divider()

    st.markdown(
        """
        <div class="ai-header">
            <div class="ai-name">
                ◈ COBAR AI
            </div>
            <div class="ai-status">
                PERSONAL INTELLIGENCE SYSTEM
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for message in st.session_state.chat:

        with st.chat_message(
            message["role"]
        ):

            st.write(
                message["content"]
            )

    prompt = st.chat_input(
        "Habla con COBAR..."
    )

    if prompt:

        st.session_state.chat.append({
            "role": "user",
            "content": prompt
        })

        context = ""

        for symbol in WATCHLIST:

            live = get_live_price(symbol)

            quote = get_quotes(
                [symbol]
            ).get(
                symbol,
                {}
            )

            if live:

                context += (
                    f"{symbol}: "
                    f"${live['price']:.2f}\n"
                )

            elif quote.get("c"):

                context += (
                    f"{symbol}: "
                    f"${quote['c']:.2f}\n"
                )

        answer = ask_cobar(
            prompt,
            context
        )

        st.session_state.chat.append({
            "role": "assistant",
            "content": answer
        })

        save_json(
            CHAT_FILE,
            st.session_state.chat
        )

        st.rerun()


# =========================================================
# MARKET
# =========================================================

elif page == "Market":

    st.markdown(
        '<div class="terminal-title">MARKET</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'REAL-TIME MARKET INTELLIGENCE'
        '</div>',
        unsafe_allow_html=True
    )

    symbol = st.text_input(
        "TICKER",
        placeholder="NVDA"
    ).upper().strip()

    if symbol:

        render_stock_card(symbol)

        chart = get_chart(symbol)

        if chart is not None:

            st.markdown(
                '<div class="section-title">'
                'PRICE HISTORY'
                '</div>',
                unsafe_allow_html=True
            )

            st.line_chart(
                chart["Price"],
                height=500
            )


# =========================================================
# INVESTMENT AI
# =========================================================

elif page == "Investment AI":

    st.markdown(
        '<div class="terminal-title">INVESTMENT AI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'SCENARIO ANALYSIS'
        '</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Herramienta educativa para analizar escenarios. "
        "No ejecuta operaciones."
    )

    capital = st.number_input(
        "CAPITAL HIPOTÉTICO",
        min_value=0.0,
        value=1000.0,
        step=100.0
    )

    horizon = st.selectbox(
        "HORIZONTE",
        [
            "Corto plazo",
            "Mediano plazo",
            "Largo plazo"
        ]
    )

    objective = st.selectbox(
        "OBJETIVO",
        [
            "Aprender",
            "Crecimiento",
            "Diversificación",
            "Entender riesgo"
        ]
    )

    details = st.text_area(
        "¿QUÉ QUIERES ANALIZAR?"
    )

    if st.button(
        "ANALIZAR ESCENARIO",
        use_container_width=True
    ):

        prompt = f"""
Analiza este escenario de forma educativa:

Capital hipotético: ${capital}

Horizonte:
{horizon}

Objetivo:
{objective}

Detalles:
{details}

Explica:

1. Qué datos habría que revisar.
2. Qué factores afectan la empresa.
3. Riesgos.
4. Escenario favorable.
5. Escenario desfavorable.
6. Qué información podría cambiar la conclusión.

No prometas ganancias.
No ejecutes operaciones.
No conectes a ningún broker.
"""

        st.write(
            ask_cobar(prompt)
        )


# =========================================================
# PORTFOLIO
# =========================================================

elif page == "Portfolio":

    st.markdown(
        '<div class="terminal-title">PORTFOLIO</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'PERSONAL HOLDINGS'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        f"Portfolio personal de {CURRENT_USER}. "
        "No está conectado a ningún broker."
    )

    with st.expander(
        "⚠ PORTFOLIO SETTINGS"
    ):

        st.warning(
            "Resetear el portfolio eliminará todas "
            "las inversiones registradas de esta cuenta."
        )

        if st.button(
            "RESET PORTFOLIO",
            type="secondary",
            use_container_width=True
        ):

            st.session_state.portfolio = []

            save_json(
                PORTFOLIO_FILE,
                []
            )

            st.success(
                "Portfolio reseteado."
            )

            st.rerun()

    st.divider()

    with st.form(
        "trade_form"
    ):

        symbol = st.text_input(
            "TICKER"
        ).upper().strip()

        shares = st.number_input(
            "CANTIDAD",
            min_value=0.0001,
            value=1.0
        )

        entry = st.number_input(
            "PRECIO DE ENTRADA",
            min_value=0.01,
            value=100.0
        )

        date = st.date_input(
            "FECHA"
        )

        submitted = st.form_submit_button(
            "GUARDAR INVERSIÓN"
        )

        if submitted and symbol:

            st.session_state.portfolio.append({
                "symbol": symbol,
                "shares": shares,
                "entry": entry,
                "date": str(date)
            })

            save_json(
                PORTFOLIO_FILE,
                st.session_state.portfolio
            )

            st.success(
                "Inversión registrada."
            )

    st.divider()

    total_cost = 0
    total_value = 0

    for trade in st.session_state.portfolio:

        symbol = trade["symbol"]

        live = get_live_price(symbol)

        quote = get_quotes(
            [symbol]
        ).get(
            symbol,
            {}
        )

        current = (
            live["price"]
            if live
            else quote.get("c")
        )

        invested = (
            trade["shares"]
            * trade["entry"]
        )

        total_cost += invested

        if current:

            value = (
                trade["shares"]
                * current
            )

            total_value += value

            pnl = (
                value
                - invested
            )

            pct = (
                pnl / invested * 100
                if invested
                else 0
            )

            st.markdown(
                f"""
                <div class="portfolio-card">

                    <div class="portfolio-symbol">
                        {symbol}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        ENTRY
                    </div>

                    <div class="portfolio-value">
                        ${trade["entry"]:,.2f}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        CURRENT
                    </div>

                    <div class="portfolio-value">
                        ${current:,.2f}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        SHARES
                    </div>

                    <div class="portfolio-value">
                        {trade["shares"]}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        P/L
                    </div>

                    <div class="metric-positive">
                        ${pnl:+,.2f}
                        &nbsp;&nbsp;
                        ({pct:+.2f}%)
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div class="portfolio-card">

                    <div class="portfolio-symbol">
                        {symbol}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        ENTRY
                    </div>

                    <div class="portfolio-value">
                        ${trade["entry"]:,.2f}
                    </div>

                    <br>

                    <div class="portfolio-data">
                        CURRENT PRICE UNAVAILABLE
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    if total_cost:

        st.divider()

        total_pnl = (
            total_value
            - total_cost
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "REGISTERED",
            f"${total_cost:,.2f}"
        )

        c2.metric(
            "CURRENT VALUE",
            f"${total_value:,.2f}"
        )

        c3.metric(
            "P/L",
            f"${total_pnl:+,.2f}"
        )

    else:

        st.info(
            "Este portfolio está vacío."
        )


# =========================================================
# NOTES
# =========================================================

elif page == "My Notes":

    st.markdown(
        '<div class="terminal-title">MY NOTES</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'PRIVATE INTELLIGENCE'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        f"Notas personales de {CURRENT_USER}."
    )

    with st.form(
        "note_form"
    ):

        title = st.text_input(
            "TÍTULO"
        )

        content = st.text_area(
            "NOTA"
        )

        save = st.form_submit_button(
            "GUARDAR NOTA"
        )

        if save and title and content:

            st.session_state.notes.append({
                "title": title,
                "content": content,
                "date": datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )
            })

            save_json(
                NOTES_FILE,
                st.session_state.notes
            )

            st.success(
                "Nota guardada."
            )

    st.divider()

    for i, note in enumerate(
        reversed(
            st.session_state.notes
        )
    ):

        st.markdown(
            f"""
            <div class="note-card">

                <div class="note-title">
                    {note["title"]}
                </div>

                <div class="note-date">
                    {note["date"]}
                </div>

                <div class="note-content">
                    {note["content"]}
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "ELIMINAR",
            key=f"delete_note_{i}"
        ):

            index = (
                len(
                    st.session_state.notes
                )
                - 1
                - i
            )

            st.session_state.notes.pop(
                index
            )

            save_json(
                NOTES_FILE,
                st.session_state.notes
            )

            st.rerun()


# =========================================================
# INTELLIGENCE FEED
# =========================================================

elif page == "Intelligence Feed":

    st.markdown(
        '<div class="terminal-title">'
        'INTELLIGENCE FEED'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'COMPANY NEWS'
        '</div>',
        unsafe_allow_html=True
    )

    symbol = st.selectbox(
        "COMPANY",
        WATCHLIST
    )

    news = get_news(symbol)

    if news:

        for item in news:

            headline = item.get(
                "headline",
                "Sin título"
            )

            source = item.get(
                "source",
                ""
            )

            url = item.get(
                "url"
            )

            st.markdown(
                f"""
                <div class="news-card">

                    <div class="news-headline">
                        {headline}
                    </div>

                    <div class="news-source">
                        {source}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

            if url:

                st.link_button(
                    "ABRIR FUENTE",
                    url
                )

    else:

        st.info(
            "No hay noticias disponibles."
        )


# =========================================================
# MEDIA
# =========================================================

elif page == "Media":

    st.markdown(
        '<div class="terminal-title">MEDIA</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="terminal-subtitle">'
        'MARKET MEDIA'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Entrevistas y videos que quieras analizar."
    )

    url = st.text_input(
        "YOUTUBE URL"
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
```
