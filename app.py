import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="Nifty & BankNifty Strategy Dashboard")
st.title("📊 Nifty & BankNifty Strategy Dashboard")
st.write("Disparity Index strategy ke saath Nifty aur BankNifty backtest karein.")

# --- Session State Initialization ---
def init_session_state():
    if 'nifty_params' not in st.session_state:
        st.session_state.nifty_params = {
            'ma_length': 29,
            'short_prd': 27,
            'long_prd': 81,
            'threshold': 0.5,
            'sl_amount': 500
        }
    if 'banknifty_params' not in st.session_state:
        st.session_state.banknifty_params = {
            'ma_length': 29,
            'short_prd': 27,
            'long_prd': 81,
            'threshold': 0.5,
            'sl_amount': 500
        }

init_session_state()

# --- Fallback Data Fetch ---
@st.cache_data
def safe_download(symbol, start, end, retries=3):
    for attempt in range(retries):
        try:
            data = yf.download(symbol, start=start, end=end)
            if not data.empty:
                return data
        except Exception:
            st.warning(f"Attempt {attempt+1}: {symbol} fetch failed — retrying...")
    st.error(f"{symbol} data fetch failed after {retries} attempts.")
    return None

# --- Indicator Calculation ---
def calculate_indicators(df, params):
    if df is None or df.empty:
        return None
    df_copy = df.copy()
    try:
        df_copy['EMA_Length'] = df_copy['Close'].ewm(span=params['ma_length'], adjust=False).mean()
        df_copy.dropna(subset=['EMA_Length'], inplace=True)
        df_copy['DI'] = ((df_copy['Close'] - df_copy['EMA_Length']) / df_copy['EMA_Length']) * 100
        df_copy['hsp_short'] = df_copy['DI'].ewm(span=params['short_prd'], adjust=False).mean()
        df_copy['hsp_long'] = df_copy['DI'].ewm(span=params['long_prd'], adjust=False).mean()
        df_copy.dropna(inplace=True)
    except Exception as e:
        st.error(f"Indicators calculate karne mein error hua: {e}")
        return None
    return df_copy

# --- Trade Log Split ---
def split_trade_log(trade_log):
    df_log = pd.DataFrame(trade_log)
    df_log['buy_date'] = pd.to_datetime(df_log['buy_date'])
    df_log['month'] = df_log['buy_date'].dt.to_period('M')
    df_log['day'] = df_log['buy_date'].dt.date
    daily_log = df_log.groupby('day').agg({'pnl': 'sum', 'buy_price': 'count'}).rename(columns={'buy_price': 'trades'})
    monthly_log = df_log.groupby('month').agg({'pnl': 'sum', 'buy_price': 'count'}).rename(columns={'buy_price': 'trades'})
    return df_log, daily_log, monthly_log

# --- Backtest Logic ---
def run_backtest_logic(index_name, df, params):
    if df is None or df.empty:
        st.warning(f"{index_name} ka backtest nahi chal paya kyuki data available nahi hai.")
        return

    st.write(f"📈 **{index_name} Backtest Results**")
    st.subheader(f"Strategy Signals ({index_name})")

    initial_capital = 100000
    trade_log = []
    in_trade = False
    open_trade = {}

    for i, (index, row) in enumerate(df.iterrows()):
        if in_trade:
            if (row['Close'] - open_trade['buy_price']) < -params['sl_amount']:
                reason = "Absolute SL"
                trade_log.append({
                    'buy_date': open_trade['buy_date'],
                    'buy_price': open_trade['buy_price'],
                    'sell_date': index.strftime('%Y-%m-%d'),
                    'sell_price': row['Close'],
                    'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital / open_trade['buy_price'])
                })
                st.write(f"🛑 **{reason}:** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
                in_trade = False
                open_trade = {}
                continue

        if row['hsp_short'] > row['hsp_long'] and not in_trade and (row['hsp_short'] - row['hsp_long']) >= params['threshold']:
            st.write(f"💼 **Buy Signal:** {index.strftime('%Y-%m-%d')} par trade shuru @ ₹{row['Close']:.2f}")
            open_trade = {'buy_date': index.strftime('%Y-%m-%d'), 'buy_price': row['Close']}
            in_trade = True

        elif row['hsp_short'] < row['hsp_long'] and in_trade:
            st.write(f"🛑 **Sell Signal:** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
            trade_log.append({
                'buy_date': open_trade['buy_date'],
                'buy_price': open_trade['buy_price'],
                'sell_date': index.strftime('%Y-%m-%d'),
                'sell_price': row['Close'],
                'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital / open_trade['buy_price'])
            })
            in_trade = False
            open_trade = {}

    final_pnl = sum(trade['pnl'] for trade in trade_log)
    total_return = (final_pnl / initial_capital) * 100

    st.subheader("Final Backtest Report")
    col1, col2, col3 = st.columns(3)
    col1.metric("Initial Capital", f"₹{initial_capital:.2f}")
    col2.metric("Total P&L", f"₹{final_pnl:.2f}")
    col3.metric("Total Return", f"{total_return:.2f}%")
    st.metric("Total Trades", len(trade_log))

    if trade_log:
        df_log, daily_log, monthly_log = split_trade_log(trade_log)
        st.subheader("📜 Trade History")
        st.dataframe(df_log)

        st.subheader("📅 Daily Summary")
        st.dataframe(daily_log)

        st.subheader("🗓️ Monthly Summary")
        st.dataframe(monthly_log)
    else:
        st.write("Is strategy ke liye koi trade nahi mila.")

# --- UI Config Inputs ---
st.subheader("Nifty 📈")
with st.expander("⚙️ Nifty Settings"):
    st.session_state.nifty_params['ma_length'] = st.number_input("Nifty MA Length", min_value=1, value=st.session_state.nifty_params['ma_length'])
    st.session_state.nifty_params['short_prd'] = st.number_input("Nifty Short Period", min_value=1, value=st.session_state.nifty_params['short_prd'])
    st.session_state.nifty_params['long_prd'] = st.number_input("Nifty Long Period", min_value=1, value=st.session_state.nifty_params['long_prd'])
    st.session_state.nifty_params['threshold'] = st.number_input("Nifty Signal Threshold (%)", min_value=0.0, value=st.session_state.nifty_params['threshold'])
    st.session_state.nifty_params['sl_amount'] = st.number_input("Nifty Stop Loss (₹)", min_value=0, value=st.session_state.nifty_params['sl_amount'])

st.subheader("BankNifty 📈")
with st.expander("⚙️ BankNifty Settings"):
    st.session_state.banknifty_params['ma_length'] = st.number_input("BankNifty MA Length", min_value=1, value=st.session_state.banknifty_params['ma_length'])
    st.session_state.banknifty_params['short_prd'] = st.number_input("BankNifty Short Period", min_value=1, value=st.session_state.banknifty_params['short_prd'])
    st.session_state.banknifty_params['long_prd'] = st.number_input("BankNifty Long Period", min_value=1, value=st.session_state.banknifty_params['long_prd'])
    st.session_state.banknifty_params['threshold'] = st.number_input("BankNifty Signal Threshold (%)", min_value=0.0, value=st.session_state.banknifty_params['threshold'])
    st.session_state.banknifty_params['sl_amount'] = st.number_input("BankNifty Stop Loss (₹)", min_value=0, value=st.session_state.banknifty_params['sl_amount'])

# --- Main Execution ---
st.header("🔄 Auto Trading &
