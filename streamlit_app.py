```python
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
            "_" o -."
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
# LOGIN
# =========================================================

def login_screen():

    st.markdown(
        """
        <style>

        .login-box {
            max-width: 500px;
            margin: 90px auto;
            padding: 40px;
            background: #030606;
            border: 1px solid #16282B;
            border-radius: 14px;
        }

        .login-title {
            font-size: 48px;
            letter-spacing: 12px;
            text-align: center;
            font-weight: 600;
        }

        .login-subtitle {
            text-align: center;
            color: #16D98A;
            font-size: 11px;
            letter-spacing: 4px;
            margin-bottom: 35px;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="login-box">',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="login-title">COBAR</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="login-subtitle">'
        'PERSONAL FINANCIAL INTELLIGENCE'
        '</div>',
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

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )


if not st.session_state.authenticated:
    login_screen()
    st.stop()


# =========================================================
# CURRENT USER
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
# DESIGN
# =========================================================

st.markdown(
    """
    <style>

    .stApp {
        background: #000000;
        color: #E8EEEE;
    }

    [data-testid="stSidebar"] {
        background: #020404;
        border-right: 1px solid #16282B;
    }

    [data-testid="stSidebar"] * {
        color: #DDE5E7;
    }

    .block-container {
        max-width: 1550px;
        padding-top: 1.5rem;
    }

    .cobar-title {
        font-size: 40px;
        letter-spacing: 10px;
        font-weight: 600;
    }

    .subtitle {
        color: #16D98A;
        font-size: 11px;
        letter-spacing: 4px;
    }

    .panel {
        background: #030606;
        border: 1px solid #16282B;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 14px;
    }

    .stock-card {
        background: #030606;
        border: 1px solid #16282B;
        border-radius: 10px;
        padding: 20px;
        min-height: 180px;
    }

    .stock-symbol {
        color: #7C8A8D;
        font-size: 11px;
        letter-spacing: 3px;
    }

    .stock-price {
        font-size: 32px;
        font-weight: 600;
        margin-top: 8px;
    }

    .stock-positive {
        color: #16D98A;
        font-size: 15px;
        font-weight: 600;
    }

    .stock-negative {
        color: #FF4F5C;
        font-size: 15px;
        font-weight: 600;
    }

    .small {
        color: #68777A;
        font-size: 10px;
        letter-spacing: 2px;
    }

    .live {
        color: #16D98A;
        font-weight: bold;
    }

    .waiting {
        color: #FFB020;
        font-weight: bold;
    }

    .offline {
        color: #FF4F5C;
        font-weight: bold;
    }

    .green {
        color: #16D98A;
    }

    .red {
        color: #FF4F5C;
    }

    .news-card {
        background: #030606;
        border: 1px solid #16282B;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 10px;
    }

    .news-title {
        font-size: 15px;
        font-weight: 600;
        line-height: 1.4;
    }

    .news-source {
        color: #68777A;
        font-size: 10px;
        letter-spacing: 2px;
        margin-top: 8px;
    }

    .account {
        background: #050909;
        border: 1px solid #193235;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }

    .note {
        background: #030606;
        border: 1px solid #16282B;
        border-radius: 9px;
        padding: 16px;
        margin-bottom: 12px;
    }

    .ai-box {
        background: #030606;
        border: 1px solid #193235;
        border-radius: 12px;
        padding: 22px;
        margin-top: 10px;
    }

    .ai-label {
        color: #16D98A;
        font-size: 11px;
        letter-spacing: 3px;
        font-weight: bold;
    }

    .status-box {
        background: #030606;
        border: 1px solid #16282B;
        border-radius: 9px;
        padding: 16px 20px;
        margin-bottom: 15px;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #050808 !important;
        color: #E8EEEE !important;
        border: 1px solid #193235 !important;
    }

    .stButton button {
        background: #050909 !important;
        color: #DCE7E7 !important;
        border: 1px solid #193235 !important;
    }

    .stButton button:hover {
        color: #16D98A !important;
        border-color: #16D98A !important;
    }

    </style>
    """,
    unsafe_allow_html=True
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

            try:
                ws.send(
                    json.dumps({
                        "type": "subscribe",
                        "symbol": symbol
                    })
                )

            except Exception:
                pass

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


def ask_cobar(question, context=""):

    if ai is None:

        return (
            "COBAR AI está offline. "
            "Revisa OPENAI_API_KEY en Streamlit Secrets."
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
        '<div class="cobar-title">COBAR</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'PERSONAL FINANCIAL INTELLIGENCE'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
        f"""
        <div class="account">
            <span class="small">
                LOGGED IN AS
            </span>
            <br>
            <b>{CURRENT_USER}</b>
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
            '<span class="live">'
            '● FINNHUB API'
            '</span>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<span class="offline">'
            '● FINNHUB KEY MISSING'
            '</span>',
            unsafe_allow_html=True
        )

    if OPENAI_KEY:

        st.markdown(
            '<span class="live">'
            '● COBAR AI'
            '</span>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<span class="offline">'
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
# MARKET DASHBOARD
# =========================================================

@st.fragment(run_every=10)
def market_dashboard():

    connected = stream_state["connected"]
    last_message = stream_state["last_message"]

    if connected and last_message:

        age = time.time() - last_message

        if age < 15:

            st.markdown(
                """
                <div class="status-box">
                    <span class="small">
                        MARKET CONNECTION
                    </span>
                    <br><br>
                    <span class="live">
                        ● LIVE STREAM
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                """
                <div class="status-box">
                    <span class="small">
                        MARKET CONNECTION
                    </span>
                    <br><br>
                    <span class="waiting">
                        ● CONNECTED / REST FALLBACK
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

    elif connected:

        st.markdown(
            """
            <div class="status-box">
                <span class="small">
                    MARKET CONNECTION
                </span>
                <br><br>
                <span class="waiting">
                    ● CONNECTED / REST FALLBACK
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="status-box">
                <span class="small">
                    MARKET CONNECTION
                </span>
                <br><br>
                <span class="waiting">
                    ● REST MARKET DATA
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )


    # -----------------------------------------------------
    # STOCK CARDS
    # -----------------------------------------------------

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

                color_class = (
                    "stock-positive"
                    if pct >= 0
                    else "stock-negative"
                )

                timestamp = datetime.fromtimestamp(
                    live["timestamp"] / 1000
                ).strftime(
                    "%H:%M:%S"
                )

                st.markdown(
                    f"""
                    <div class="stock-card">

                        <div class="stock-symbol">
                            {symbol}
                        </div>

                        <div class="stock-price">
                            ${price:,.2f}
                        </div>

                        <div class="{color_class}">
                            {pct:+.2f}%
                        </div>

                        <br>

                        <div class="live">
                            ● LIVE · {timestamp}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            elif quote.get("c"):

                price = quote["c"]

                pct = quote.get(
                    "dp",
                    0
                )

                color_class = (
                    "stock-positive"
                    if pct >= 0
                    else "stock-negative"
                )

                st.markdown(
                    f"""
                    <div class="stock-card">

                        <div class="stock-symbol">
                            {symbol}
                        </div>

                        <div class="stock-price">
                            ${price:,.2f}
                        </div>

                        <div class="{color_class}">
                            {pct:+.2f}%
                        </div>

                        <br>

                        <div class="waiting">
                            ● REST DATA
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f"""
                    <div class="stock-card">

                        <div class="stock-symbol">
                            {symbol}
                        </div>

                        <div class="stock-price">
                            N/D
                        </div>

                        <br>

                        <div class="offline">
                            ● NO DATA
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


    # -----------------------------------------------------
    # CHART
    # -----------------------------------------------------

    st.markdown(
        "<br><div class='small'>LIVE MARKET CHART</div>",
        unsafe_allow_html=True
    )

    selected = st.selectbox(
        "SYMBOL",
        WATCHLIST,
        key="dashboard_symbol"
    )

    live = get_live_price(selected)

    if live:

        st.metric(
            "LIVE PRICE",
            f"${live['price']:,.2f}"
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
        """
        <div class="cobar-title">
            COBAR
        </div>

        <div class="subtitle">
            PERSONAL FINANCIAL INTELLIGENCE
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    market_dashboard()

    st.divider()

    # -----------------------------------------------------
    # NEWS
    # -----------------------------------------------------

    st.subheader("📡 MARKET NEWS")

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
                ""
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

    # -----------------------------------------------------
    # COBAR AI
    # -----------------------------------------------------

    st.markdown(
        """
        <div class="ai-box">

            <div class="ai-label">
                ◈ COBAR AI
            </div>

            <div style="
                color:#68777A;
                font-size:12px;
                margin-top:7px;
            ">
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
        "Pregunta a COBAR sobre mercados, empresas o tecnología..."
    )


    if prompt:

        st.session_state.chat.append({
            "role": "user",
            "content": prompt
        })

        context = ""

        quotes = get_quotes(
            WATCHLIST
        )

        for symbol in WATCHLIST:

            quote = quotes.get(
                symbol,
                {}
            )

            if quote.get("c"):

                context += (
                    f"{symbol}: "
                    f"${quote['c']:.2f} "
                    f"({quote.get('dp', 0):+.2f}%)\n"
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

    st.title("MARKET")

    st.caption(
        "Market data provided through Finnhub."
    )

    symbol = st.text_input(
        "Ticker",
        placeholder="NVDA"
    ).upper().strip()

    if symbol:

        live = get_live_price(symbol)

        quote = get_quotes(
            [symbol]
        ).get(
            symbol,
            {}
        )

        if live:

            st.metric(
                "LIVE PRICE",
                f"${live['price']:,.2f}"
            )

            st.caption(
                "● LIVE STREAM"
            )

        elif quote.get("c"):

            st.metric(
                "PRICE",
                f"${quote['c']:,.2f}"
            )

            st.caption(
                "● REST DATA"
            )

        else:

            st.error(
                "No se encontraron datos para ese ticker."
            )

        chart = get_chart(symbol)

        if chart is not None:

            st.line_chart(
                chart["Price"],
                height=500
            )


# =========================================================
# INVESTMENT AI
# =========================================================

elif page == "Investment AI":

    st.title("INVESTMENT AI")

    st.caption(
        "Herramienta educativa para analizar escenarios. "
        "No ejecuta operaciones."
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

        st.markdown(
            """
            <div class="ai-box">
                <div class="ai-label">
                    ◈ COBAR ANALYSIS
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(
            ask_cobar(prompt)
        )


# =========================================================
# PORTFOLIO
# =========================================================

elif page == "Portfolio":

    st.title("PORTFOLIO")

    st.caption(
        f"Portfolio personal de {CURRENT_USER}. "
        "No está conectado a ningún broker."
    )


    # -----------------------------------------------------
    # RESET
    # -----------------------------------------------------

    with st.expander(
        "⚠️ Portfolio settings"
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
                "Portfolio reseteado."
            )

            st.rerun()


    st.divider()


    # -----------------------------------------------------
    # ADD INVESTMENT
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # PORTFOLIO DATA
    # -----------------------------------------------------

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

            color_class = (
                "green"
                if pnl >= 0
                else "red"
            )

            st.markdown(
                f"""
                <div class="note">

                    <h3>
                        {symbol}
                    </h3>

                    <span class="small">
                        POSITION
                    </span>

                    <br><br>

                    Entrada:
                    ${trade["entry"]:,.2f}

                    <br>

                    Actual:
                    ${current:,.2f}

                    <br>

                    Cantidad:
                    {trade["shares"]}

                    <br><br>

                    <span class="{color_class}">
                        P/L:
                        ${pnl:+,.2f}
                        ({pct:+.2f}%)
                    </span>

                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                f"""
                <div class="note">

                    <h3>{symbol}</h3>

                    <span class="small">
                        POSITION
                    </span>

                    <br><br>

                    Entrada:
                    ${trade["entry"]:,.2f}

                    <br>

                    Cantidad:
                    {trade["shares"]}

                    <br><br>

                    <span class="waiting">
                        ● MARKET DATA UNAVAILABLE
                    </span>

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

    else:

        st.info(
            "Este portfolio está vacío."
        )


# =========================================================
# NOTES
# =========================================================

elif page == "My Notes":

    st.title("MY NOTES")

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
            <div class="note">

                <h3>
                    {note["title"]}
                </h3>

                <span class="small">
                    {note["date"]}
                </span>

                <br><br>

                {note["content"]}

            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "Eliminar",
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

    st.title(
        "INTELLIGENCE FEED"
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
                ""
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

    st.title("MEDIA")

    st.caption(
        "Entrevistas y videos que quieras analizar."
    )

    url = st.text_input(
        "URL de YouTube"
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
