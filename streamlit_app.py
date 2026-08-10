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


# =========================================================
# API KEYS
# =========================================================

FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")
OPENAI_KEY = st.secrets.get("OPENAI_API_KEY", "")


# =========================================================
# GLOBAL DESIGN
# =========================================================

st.markdown(
    """
    <style>

    /* ==============================
       GLOBAL
       ============================== */

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                #061311 0%,
                #000000 35%,
                #000000 100%
            );
        color: #E8EEEE;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        background: #020404;
        border-right: 1px solid #142522;
    }

    [data-testid="stSidebar"] * {
        color: #DDE8E6 !important;
    }


    /* ==============================
       COBAR HEADER
       ============================== */

    .cobar-logo {
        font-size: 44px;
        font-weight: 600;
        letter-spacing: 12px;
        color: #EAF5F2;
        margin-bottom: 2px;
    }

    .cobar-subtitle {
        font-size: 10px;
        letter-spacing: 4px;
        color: #16D98A;
        margin-bottom: 25px;
    }


    /* ==============================
       PANELS
       ============================== */

    .cobar-panel {
        background:
            linear-gradient(
                145deg,
                #07100E 0%,
                #030706 100%
            );
        border: 1px solid #17342E;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 16px;
        box-shadow:
            0 8px 30px rgba(0, 0, 0, 0.35);
    }

    .market-card {
        background:
            linear-gradient(
                145deg,
                #081310 0%,
                #030706 100%
            );
        border: 1px solid #173D33;
        border-radius: 15px;
        padding: 22px;
        min-height: 190px;
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.025),
            0 10px 30px rgba(0,0,0,0.35);
    }

    .market-card:hover {
        border-color: #16D98A;
    }

    .ticker {
        color: #78908B;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 3px;
    }

    .stock-price {
        color: #F2F8F6;
        font-size: 34px;
        font-weight: 600;
        margin-top: 12px;
        margin-bottom: 5px;
    }

    .positive {
        color: #16D98A;
        font-size: 16px;
        font-weight: 600;
    }

    .negative {
        color: #FF5964;
        font-size: 16px;
        font-weight: 600;
    }

    .live-label {
        color: #16D98A;
        font-size: 10px;
        letter-spacing: 2px;
        font-weight: 600;
    }

    .rest-label {
        color: #7D918D;
        font-size: 10px;
        letter-spacing: 2px;
    }

    .offline-label {
        color: #FF5964;
        font-size: 10px;
        letter-spacing: 2px;
    }


    /* ==============================
       SECTION TITLES
       ============================== */

    .section-title {
        color: #EAF5F2;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 2px;
        margin-top: 10px;
        margin-bottom: 16px;
    }

    .section-label {
        color: #657A76;
        font-size: 10px;
        letter-spacing: 3px;
        text-transform: uppercase;
    }


    /* ==============================
       NEWS
       ============================== */

    .news-card {
        background: #040907;
        border: 1px solid #132B26;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 10px;
    }

    .news-title {
        color: #E6EFED;
        font-size: 15px;
        font-weight: 500;
        line-height: 1.45;
    }

    .news-source {
        color: #627772;
        font-size: 10px;
        letter-spacing: 2px;
        margin-top: 8px;
    }


    /* ==============================
       AI
       ============================== */

    .ai-header {
        background:
            linear-gradient(
                135deg,
                #06130F,
                #020505
            );
        border: 1px solid #1B493D;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 15px;
    }

    .ai-title {
        color: #16D98A;
        font-size: 17px;
        font-weight: 600;
        letter-spacing: 3px;
    }

    .ai-subtitle {
        color: #71847F;
        font-size: 11px;
        margin-top: 5px;
    }


    /* ==============================
       PORTFOLIO
       ============================== */

    .portfolio-card {
        background:
            linear-gradient(
                145deg,
                #07100E,
                #030605
            );
        border: 1px solid #17342E;
        border-radius: 13px;
        padding: 20px;
        margin-bottom: 12px;
    }

    .portfolio-symbol {
        color: #16D98A;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 2px;
    }

    .portfolio-value {
        color: #F0F6F4;
        font-size: 25px;
        font-weight: 600;
    }


    /* ==============================
       NOTES
       ============================== */

    .note-card {
        background: #040807;
        border: 1px solid #18322C;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .note-title {
        color: #EAF2F0;
        font-size: 17px;
        font-weight: 600;
    }

    .note-date {
        color: #647A74;
        font-size: 10px;
        letter-spacing: 2px;
    }


    /* ==============================
       INPUTS
       ============================== */

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #030706 !important;
        color: #E8EEEE !important;
        border: 1px solid #17342E !important;
        border-radius: 8px !important;
    }

    .stSelectbox div[data-baseweb="select"] {
        background: #030706 !important;
    }


    /* ==============================
       BUTTONS
       ============================== */

    .stButton button {
        background: #06100D !important;
        color: #DDE9E6 !important;
        border: 1px solid #1A4036 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    .stButton button:hover {
        color: #16D98A !important;
        border-color: #16D98A !important;
        background: #071712 !important;
    }


    /* ==============================
       METRICS
       ============================== */

    [data-testid="stMetric"] {
        background: #040907;
        border: 1px solid #17342E;
        border-radius: 12px;
        padding: 15px;
    }

    [data-testid="stMetricValue"] {
        color: #EAF5F2;
    }

    [data-testid="stMetricLabel"] {
        color: #71847F;
    }


    /* ==============================
       CHAT
       ============================== */

    [data-testid="stChatMessage"] {
        background: #030706;
        border: 1px solid #142B26;
        border-radius: 12px;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# JSON / USERS
# =========================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception:
        return default


def save_json(filename, data):

    directory = os.path.dirname(filename)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True
        )

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

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


def check_password(
    password,
    salt,
    stored_hash
):

    _, calculated = hash_password(
        password,
        salt
    )

    return hmac.compare_digest(
        calculated,
        stored_hash
    )


def create_account(
    username,
    password
):

    username = normalize_username(
        username
    )

    users = load_json(
        USERS_FILE,
        {}
    )

    if username in users:
        return False, "Ese usuario ya existe."

    if not valid_username(username):
        return False, (
            "El usuario debe tener entre "
            "3 y 24 caracteres y solo usar "
            "letras, números, _ o -."
        )

    if len(password) < 6:
        return False, (
            "La contraseña debe tener al "
            "menos 6 caracteres."
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


def login(
    username,
    password
):

    username = normalize_username(
        username
    )

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
# LOGIN
# =========================================================

def login_screen():

    st.markdown(
        "<div style='height:80px'></div>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        st.markdown(
            """
            <div class="cobar-panel"
                 style="text-align:center; padding:40px;">
                <div class="cobar-logo">
                    COBAR
                </div>

                <div class="cobar-subtitle">
                    PERSONAL FINANCIAL INTELLIGENCE
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        mode = st.radio(
            "ACCESS",
            [
                "Log in",
                "Create account"
            ],
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
                            "Cuenta creada. "
                            "Ahora puedes iniciar sesión."
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
# CURRENT USER
# =========================================================

CURRENT_USER = (
    st.session_state.username
)

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


fh = create_finnhub(
    FINNHUB_KEY
)


@st.cache_data(ttl=10)
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

        df = pd.DataFrame(
            {
                "Time": pd.to_datetime(
                    data["t"],
                    unit="s"
                ),
                "Price": data["c"]
            }
        )

        return df.set_index("Time")

    except Exception:

        return None


@st.cache_data(ttl=120)
def get_news(symbol):

    if fh is None:
        return []

    try:

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )

        news = fh.company_news(
            symbol,
            _from=today,
            to=today
        )

        return news[:10]

    except Exception:

        return []


# =========================================================
# LIVE FINNHUB WEBSOCKET
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

            try:

                ws.send(
                    json.dumps(
                        {
                            "type": "subscribe",
                            "symbol": symbol
                        }
                    )
                )

            except Exception:
                pass


    def on_message(
        ws,
        message
    ):

        try:

            data = json.loads(
                message
            )

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

                    if (
                        symbol
                        and price is not None
                    ):

                        prices[symbol] = {
                            "price": float(price),
                            "timestamp": int(
                                timestamp
                            )
                        }

                        state["last_message"] = (
                            time.time()
                        )

        except Exception as e:

            state["error"] = str(e)


    def on_error(
        ws,
        error
    ):

        state["connected"] = False
        state["error"] = str(error)


    def on_close(
        ws,
        code,
        msg
    ):

        state["connected"] = False


    def run():

        while True:

            try:

                ws = websocket.WebSocketApp(
                    "wss://ws.finnhub.io"
                    f"?token={key}",
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

        return prices.get(
            symbol
        )


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
You are COBAR, a private personal financial
intelligence assistant.

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
            model="gpt-4.1",
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
        """
        <div class="cobar-logo">
            COBAR
        </div>

        <div class="cobar-subtitle">
            PERSONAL FINANCIAL INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
        f"""
        <div class="cobar-panel">

            <div class="section-label">
                LOGGED IN AS
            </div>

            <div style="
                font-size:17px;
                margin-top:6px;
                color:#EAF5F2;
            ">
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
            """
            <div class="live-label">
                ● FINNHUB API
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="offline-label">
                ● FINNHUB KEY MISSING
            </div>
            """,
            unsafe_allow_html=True
        )

    if OPENAI_KEY:

        st.markdown(
            """
            <div class="live-label">
                ● COBAR AI
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="offline-label">
                ● OPENAI KEY MISSING
            </div>
            """,
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
# MARKET CARDS
# =========================================================

def render_market_card(
    symbol
):

    live = get_live_price(
        symbol
    )

    quote = get_quotes(
        [symbol]
    ).get(
        symbol,
        {}
    )

    if live:

        price = live["price"]

        previous = quote.get(
            "pc"
        )

        if previous:

            pct = (
                (price - previous)
                / previous
                * 100
            )

        else:

            pct = quote.get(
                "dp",
                0
            )

        if pct >= 0:

            movement_class = "positive"

        else:

            movement_class = "negative"

        timestamp = datetime.fromtimestamp(
            live["timestamp"] / 1000
        ).strftime(
            "%H:%M:%S"
        )

        html = f"""
        <div class="market-card">

            <div class="ticker">
                {symbol}
            </div>

            <div class="stock-price">
                ${price:,.2f}
            </div>

            <div class="{movement_class}">
                {pct:+.2f}%
            </div>

            <div style="height:20px"></div>

            <div class="live-label">
                ● LIVE · {timestamp}
            </div>

        </div>
        """

    elif quote.get("c"):

        price = quote["c"]

        pct = quote.get(
            "dp",
            0
        )

        if pct >= 0:

            movement_class = "positive"

        else:

            movement_class = "negative"

        html = f"""
        <div class="market-card">

            <div class="ticker">
                {symbol}
            </div>

            <div class="stock-price">
                ${price:,.2f}
            </div>

            <div class="{movement_class}">
                {pct:+.2f}%
            </div>

            <div style="height:20px"></div>

            <div class="rest-label">
                ● REST MARKET DATA
            </div>

        </div>
        """

    else:

        html = f"""
        <div class="market-card">

            <div class="ticker">
                {symbol}
            </div>

            <div class="stock-price">
                N/D
            </div>

            <div class="offline-label">
                DATA UNAVAILABLE
            </div>

        </div>
        """

    st.markdown(
        html,
        unsafe_allow_html=True
    )


# =========================================================
# MARKET DASHBOARD
# =========================================================

def market_dashboard():

    connected = stream_state["connected"]
    last_message = stream_state["last_message"]

    if connected and last_message:

        age = time.time() - last_message

        if age < 15:

            connection_text = (
                "● LIVE MARKET STREAM"
            )

            connection_class = "live-label"

        else:

            connection_text = (
                "● CONNECTED / WAITING"
            )

            connection_class = "rest-label"

    elif connected:

        connection_text = (
            "● CONNECTED / WAITING FOR TICKS"
        )

        connection_class = "rest-label"

    else:

        connection_text = (
            "● STREAM OFFLINE · REST DATA ACTIVE"
        )

        connection_class = "offline-label"


    st.markdown(
        f"""
        <div class="cobar-panel">

            <div class="section-label">
                MARKET CONNECTION
            </div>

            <div class="{connection_class}"
                 style="font-size:13px; margin-top:8px;">
                {connection_text}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )


    row1 = st.columns(4)

    for col, symbol in zip(
        row1,
        [
            "NVDA",
            "TSLA",
            "AAPL",
            "MSFT"
        ]
    ):

        with col:

            render_market_card(
                symbol
            )


    st.markdown(
        "<div style='height:8px'></div>",
        unsafe_allow_html=True
    )


    row2 = st.columns(4)

    for col, symbol in zip(
        row2,
        [
            "AMZN",
            "META",
            "AMD",
            "GOOGL"
        ]
    ):

        with col:

            render_market_card(
                symbol
            )


    st.markdown(
        """
        <div class="section-title">
            PRICE CHART
        </div>
        """,
        unsafe_allow_html=True
    )


    selected = st.selectbox(
        "SYMBOL",
        WATCHLIST,
        key="dashboard_symbol"
    )


    live = get_live_price(
        selected
    )

    if live:

        st.metric(
            "LIVE PRICE",
            f"${live['price']:,.2f}"
        )

        st.caption(
            "● LIVE STREAM"
        )


    chart = get_chart(
        selected
    )


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
        """
        <div class="cobar-logo">
            COBAR
        </div>

        <div class="cobar-subtitle">
            PERSONAL FINANCIAL INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )

    market_dashboard()

    st.divider()

    st.markdown(
        """
        <div class="section-title">
            📡 MARKET INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )

    news_symbol = st.selectbox(
        "Company",
        WATCHLIST,
        key="command_news"
    )

    news = get_news(
        news_symbol
    )

    if news:

        for item in news:

            headline = item.get(
                "headline",
                "Untitled"
            )

            source = item.get(
                "source",
                "Unknown"
            )

            st.markdown(
                f"""
                <div class="news-card">

                    <div class="news-title">
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

            <div class="ai-title">
                ◈ COBAR AI
            </div>

            <div class="ai-subtitle">
                PERSONAL FINANCIAL INTELLIGENCE
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
        "Ask COBAR about a company, market or idea..."
    )


    if prompt:

        st.session_state.chat.append(
            {
                "role": "user",
                "content": prompt
            }
        )


        context = ""

        for symbol in WATCHLIST:

            live = get_live_price(
                symbol
            )

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


        st.session_state.chat.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


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
        """
        <div class="cobar-logo">
            MARKET
        </div>

        <div class="cobar-subtitle">
            LIVE MARKET INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )


    symbol = st.text_input(
        "Ticker",
        placeholder="NVDA"
    ).upper().strip()


    if symbol:

        render_market_card(
            symbol
        )

        chart = get_chart(
            symbol
        )

        if chart is not None:

            st.markdown(
                """
                <div class="section-title">
                    PRICE HISTORY
                </div>
                """,
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
        """
        <div class="cobar-logo">
            INVESTMENT AI
        </div>

        <div class="cobar-subtitle">
            EDUCATIONAL MARKET ANALYSIS
        </div>
        """,
        unsafe_allow_html=True
    )


    st.info(
        "Herramienta educativa. COBAR no ejecuta operaciones "
        "ni se conecta a brokers."
    )


    capital = st.number_input(
        "Capital hipotético",
        min_value=0.0,
        value=1000.0,
        step=100.0
    )


    horizon = st.selectbox(
        "Horizonte",
        [
            "Corto plazo",
            "Mediano plazo",
            "Largo plazo"
        ]
    )


    objective = st.selectbox(
        "Objetivo",
        [
            "Aprender",
            "Crecimiento",
            "Diversificación",
            "Entender riesgo"
        ]
    )


    details = st.text_area(
        "¿Qué quieres analizar?"
    )


    if st.button(
        "ANALIZAR",
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
            ask_cobar(
                prompt
            )
        )


# =========================================================
# PORTFOLIO
# =========================================================

elif page == "Portfolio":

    st.markdown(
        """
        <div class="cobar-logo">
            PORTFOLIO
        </div>

        <div class="cobar-subtitle">
            PERSONAL INVESTMENT TRACKER
        </div>
        """,
        unsafe_allow_html=True
    )


    st.caption(
        f"Portfolio personal de {CURRENT_USER}. "
        "No está conectado a ningún broker."
    )


    # -----------------------------------------------------
    # RESET PORTFOLIO
    # -----------------------------------------------------

    with st.expander(
        "⚙ PORTFOLIO SETTINGS"
    ):

        st.warning(
            "Resetear el portfolio eliminará "
            "todas las inversiones registradas "
            "de esta cuenta."
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
                "Portfolio reseteado correctamente."
            )

            st.rerun()


    st.divider()


    with st.form(
        "trade_form"
    ):

        symbol = st.text_input(
            "Ticker"
        ).upper().strip()


        shares = st.number_input(
            "Cantidad",
            min_value=0.0001,
            value=1.0
        )


        entry = st.number_input(
            "Precio de entrada",
            min_value=0.01,
            value=100.0
        )


        date = st.date_input(
            "Fecha"
        )


        submitted = st.form_submit_button(
            "GUARDAR INVERSIÓN"
        )


        if submitted and symbol:

            st.session_state.portfolio.append(
                {
                    "symbol": symbol,
                    "shares": shares,
                    "entry": entry,
                    "date": str(date)
                }
            )


            save_json(
                PORTFOLIO_FILE,
                st.session_state.portfolio
            )


            st.success(
                "Inversión registrada."
            )


    st.divider()


    total_cost = 0.0
    total_value = 0.0


    if not st.session_state.portfolio:

        st.info(
            "Este portfolio está vacío."
        )


    for trade in st.session_state.portfolio:

        symbol = trade["symbol"]

        live = get_live_price(
            symbol
        )

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


            if pnl >= 0:

                movement_class = "positive"

            else:

                movement_class = "negative"


            st.markdown(
                f"""
                <div class="portfolio-card">

                    <div class="portfolio-symbol">
                        {symbol}
                    </div>

                    <div style="height:10px"></div>

                    <div class="portfolio-value">
                        ${value:,.2f}
                    </div>

                    <div style="height:8px"></div>

                    <div>
                        Entrada:
                        ${trade["entry"]:,.2f}
                    </div>

                    <div>
                        Actual:
                        ${current:,.2f}
                    </div>

                    <div>
                        Cantidad:
                        {trade["shares"]}
                    </div>

                    <div style="height:10px"></div>

                    <div class="{movement_class}">
                        P/L:
                        ${pnl:+,.2f}
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

                    <div style="height:10px"></div>

                    <div class="portfolio-value">
                        DATA UNAVAILABLE
                    </div>

                    <div>
                        Entrada:
                        ${trade["entry"]:,.2f}
                    </div>

                    <div>
                        Cantidad:
                        {trade["shares"]}
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
            "REGISTRADO",
            f"${total_cost:,.2f}"
        )


        c2.metric(
            "VALOR ACTUAL",
            f"${total_value:,.2f}"
        )


        c3.metric(
            "P/L",
            f"${total_pnl:+,.2f}"
        )


# =========================================================
# MY NOTES
# =========================================================

elif page == "My Notes":

    st.markdown(
        """
        <div class="cobar-logo">
            MY NOTES
        </div>

        <div class="cobar-subtitle">
            PRIVATE KNOWLEDGE
        </div>
        """,
        unsafe_allow_html=True
    )


    st.caption(
        f"Notas personales de {CURRENT_USER}."
    )


    with st.form(
        "note_form"
    ):

        title = st.text_input(
            "Título"
        )


        content = st.text_area(
            "Nota"
        )


        save = st.form_submit_button(
            "GUARDAR NOTA"
        )


        if save and title and content:

            st.session_state.notes.append(
                {
                    "title": title,
                    "content": content,
                    "date": datetime.now().strftime(
                        "%d/%m/%Y %H:%M"
                    )
                }
            )


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

                <div style="height:12px"></div>

                <div>
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
        """
        <div class="cobar-logo">
            INTELLIGENCE FEED
        </div>

        <div class="cobar-subtitle">
            COMPANY NEWS
        </div>
        """,
        unsafe_allow_html=True
    )


    symbol = st.selectbox(
        "Empresa",
        WATCHLIST
    )


    news = get_news(
        symbol
    )


    if news:

        for item in news:

            headline = item.get(
                "headline",
                "Sin título"
            )


            source = item.get(
                "source",
                "Unknown"
            )


            url = item.get(
                "url"
            )


            st.markdown(
                f"""
                <div class="news-card">

                    <div class="news-title">
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
                    "OPEN SOURCE",
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
        """
        <div class="cobar-logo">
            MEDIA
        </div>

        <div class="cobar-subtitle">
            VIDEO INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )


    st.caption(
        "Entrevistas y videos que quieras analizar."
    )


    url = st.text_input(
        "YouTube URL"
    )


    if url:

        if (
            "youtube.com" in url
            or "youtu.be" in url
        ):

            st.video(
                url
            )

        else:

            st.error(
                "Introduce una URL de YouTube válida."
            )
