# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="Nifty & BankNifty Strategy Dashboard")

st.title("📊 Nifty & BankNifty Strategy Dashboard")
st.write("Disparity Index strategy ke saath Nifty aur BankNifty backtest karein.")

# --- Session State Initialization ---
# Session state ka upyog inputs ko yaad rakhne ke liye kiya ja raha hai
if 'nifty_ma_length' not in st.session_state:
    st.session_state.nifty_ma_length = 29
    st.session_state.nifty_short_prd = 27
    st.session_state.nifty_long_prd = 81
    st.session_state.nifty_threshold = 0.5
    st.session_state.nifty_sl_amount = 500
    st.session_state.nifty_trail_sl_percent = 5
    st.session_state.banknifty_ma_length = 29
    st.session_state.banknifty_short_prd = 27
    st.session_state.banknifty_long_prd = 81
    st.session_state.banknifty_threshold = 0.5
    st.session_state.banknifty_sl_amount = 500
    st.session_state.banknifty_trail_sl_percent = 5

# --- Data Functions ---
@st.cache_data
def get_historical_data(symbol, start_date, end_date):
    try:
        data = yf.download(symbol, start=start_date, end=end_date)
        if data.empty:
            return None
        return data
    except Exception as e:
        st.error(f"Data download karte samay error hua: {e}. Kripya sahi symbol check karein.")
        return None

def calculate_indicators(df, length, short_period, long_period):
    df['EMA_Length'] = df['Close'].ewm(span=length, adjust=False).mean()
    df['DI'] = ((df['Close'] - df['EMA_Length']) / df['EMA_Length']) * 100
    df['hsp_short'] = df['DI'].ewm(span=short_period, adjust=False).mean()
    df['hsp_long'] = df['DI'].ewm(span=long_period, adjust=False).mean()
    return df

# --- Backtest Logic ---
def run_backtest(index_name, df, ma_length, short_prd, long_prd, threshold, sl_amount, trail_sl_percent):
    if df is None or df.empty:
        st.write(f"📈 **{index_name} Backtest Results**")
        st.warning(f"{index_name} ke liye data available nahi hai.")
        return

    # Calculate indicators
    df = calculate_indicators(df, ma_length, short_prd, long_prd)

    # Backtest logic
    initial_capital = 100000
    positions = []
    trade_log = []

    st.write(f"📈 **{index_name} Backtest Results**")
    st.subheader(f"Strategy Signals ({index_name})")
    
    # Generate signals based on the crossover and threshold
    df['Signal'] = 0.0
    df['Signal'] = (df['hsp_short'] > df['hsp_long']).astype(int)
    
    in_trade = False
    open_trade = {}
    
    for i, (index, row) in enumerate(df.iterrows()):
        # Check for open position and trailing stop loss
        if in_trade:
            # Trailing Stop Loss logic
            # Price ke bajay Close ka upyog kiya gaya hai
            current_profit = row['Close'] - open_trade['buy_price']
            if current_profit < 0 and abs(current_profit) >= sl_amount:
                # Absolute stop loss
                st.write(f"🛑 **Stop Loss (Absolute):** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
                
                trade_log.append({
                    'buy_date': open_trade['buy_date'],
                    'buy_price': open_trade['buy_price'],
                    'sell_date': index.strftime('%Y-%m-%d'),
                    'sell_price': row['Close'],
                    'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital/open_trade['buy_price'])
                })
                in_trade = False
                open_trade = {}
            elif current_profit > 0:
                # Trailing stop loss
                trail_sl_price = open_trade['buy_price'] + (open_trade['buy_price'] * (trail_sl_percent / 100))
                if row['Close'] < trail_sl_price:
                    st.write(f"🛑 **Stop Loss (Trailing):** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
                    trade_log.append({
                        'buy_date': open_trade['buy_date'],
                        'buy_price': open_trade['buy_price'],
                        'sell_date': index.strftime('%Y-%m-%d'),
                        'sell_price': row['Close'],
                        'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital/open_trade['buy_price'])
                    })
                    in_trade = False
                    open_trade = {}
        
        # Check for buy signal
        if row['hsp_short'] > row['hsp_long'] and not in_trade:
            if row['hsp_short'] - row['hsp_long'] >= threshold:
                st.write(f"💼 **Buy Signal:** {index.strftime('%Y-%m-%d')} par trade shuru @ ₹{row['Close']:.2f}")
                open_trade = {'buy_date': index.strftime('%Y-%m-%d'), 'buy_price': row['Close']}
                in_trade = True
        
        # Check for sell signal
        elif row['hsp_short'] < row['hsp_long'] and in_trade:
            st.write(f"🛑 **Sell Signal:** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
            trade_log.append({
                'buy_date': open_trade['buy_date'],
                'buy_price': open_trade['buy_price'],
                'sell_date': index.strftime('%Y-%m-%d'),
                'sell_price': row['Close'],
                'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital/open_trade['buy_price'])
            })
            in_trade = False
            open_trade = {}

    # Final P&L calculation
    final_pnl = sum([trade['pnl'] for trade in trade_log])
    total_return = (final_pnl / initial_capital) * 100

    st.subheader("Final Backtest Report")
    col1, col2, col3 = st.columns(3)
    col1.metric("Initial Capital", f"₹{initial_capital:.2f}")
    col2.metric("Total P&L", f"₹{final_pnl:.2f}")
    col3.metric("Total Return", f"{total_return:.2f}%")
    st.metric("Total Trades", len(trade_log))

    if trade_log:
        st.subheader("Trade History")
        st.dataframe(pd.DataFrame(trade_log))
    else:
        st.write("Is strategy ke liye koi trade nahi mila.")

# --- Main Logic ---
st.subheader("Nifty 📈")
with st.expander("⚙️ Nifty Settings"):
    st.session_state.nifty_ma_length = st.number_input("Nifty MA Length", min_value=1, value=st.session_state.nifty_ma_length)
    st.session_state.nifty_short_prd = st.number_input("Nifty Short Period", min_value=1, value=st.session_state.nifty_short_prd)
    st.session_state.nifty_long_prd = st.number_input("Nifty Long Period", min_value=1, value=st.session_state.nifty_long_prd)
    st.session_state.nifty_threshold = st.number_input("Nifty Signal Threshold (%)", min_value=0.0, value=st.session_state.nifty_threshold)
    st.session_state.nifty_sl_amount = st.number_input("Nifty Stop Loss (₹)", min_value=0, value=st.session_state.nifty_sl_amount)
    st.session_state.nifty_trail_sl_percent = st.number_input("Nifty Trailing SL (%)", min_value=0, value=st.session_state.nifty_trail_sl_percent)

st.subheader("BankNifty 📈")
with st.expander("⚙️ BankNifty Settings"):
    st.session_state.banknifty_ma_length = st.number_input("BankNifty MA Length", min_value=1, value=st.session_state.banknifty_ma_length)
    st.session_state.banknifty_short_prd = st.number_input("BankNifty Short Period", min_value=1, value=st.session_state.banknifty_short_prd)
    st.session_state.banknifty_long_prd = st.number_input("BankNifty Long Period", min_value=1, value=st.session_state.banknifty_long_prd)
    st.session_state.banknifty_threshold = st.number_input("BankNifty Signal Threshold (%)", min_value=0.0, value=st.session_state.banknifty_threshold)
    st.session_state.banknifty_sl_amount = st.number_input("BankNifty Stop Loss (₹)", min_value=0, value=st.session_state.banknifty_sl_amount)
    st.session_state.banknifty_trail_sl_percent = st.number_input("BankNifty Trailing SL (%)", min_value=0, value=st.session_state.banknifty_trail_sl_percent)

st.header("🔄 Auto Trading & ⏱️ Backtesting")
run_backtest_button = st.button("Run Backtest", key="run_all")

if run_backtest_button:
    st.write("Generating and backtesting 5 years of historical data. This may take a while...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365) # 5 saal ka data
    
    df_nifty = get_historical_data("^NSEI", start_date, end_date)
    df_banknifty = get_historical_data("^NSEBANK", start_date, end_date)

    if df_nifty is not None and not df_nifty.empty:
        run_backtest('Nifty', df_nifty.copy(), st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold, st.session_state.nifty_sl_amount, st.session_state.nifty_trail_sl_percent)
    else:
        st.error("Nifty data download karne mein error hua.")

    st.write("---")

    if df_banknifty is not None and not df_banknifty.empty:
        run_backtest('BankNifty', df_banknifty.copy(), st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold, st.session_state.banknifty_sl_amount, st.session_state.banknifty_trail_sl_percent)
    else:
        st.error("BankNifty data download karne mein error hua.")

                'buy_date': open_trade['buy_date'],
                'buy_price': open_trade['buy_price'],
                'sell_date': index.strftime('%Y-%m-%d'),
                'sell_price': row['Close'],
                'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital/open_trade['buy_price'])
            })
            in_trade = False
            open_trade = {}

    # Final P&L calculation
    final_pnl = sum([trade['pnl'] for trade in trade_log])
    total_return = (final_pnl / initial_capital) * 100

    st.subheader("Final Backtest Report")
    col1, col2, col3 = st.columns(3)
    col1.metric("Initial Capital", f"₹{initial_capital:.2f}")
    col2.metric("Total P&L", f"₹{final_pnl:.2f}")
    col3.metric("Total Return", f"{total_return:.2f}%")
    st.metric("Total Trades", len(trade_log))

    if trade_log:
        st.subheader("Trade History")
        st.dataframe(pd.DataFrame(trade_log))
    else:
        st.write("Is strategy ke liye koi trade nahi mila.")

# --- Main Logic ---
st.subheader("Nifty 📈")
with st.expander("⚙️ Nifty Settings"):
    st.session_state.nifty_ma_length = st.number_input("Nifty MA Length", min_value=1, value=st.session_state.nifty_ma_length)
    st.session_state.nifty_short_prd = st.number_input("Nifty Short Period", min_value=1, value=st.session_state.nifty_short_prd)
    st.session_state.nifty_long_prd = st.number_input("Nifty Long Period", min_value=1, value=st.session_state.nifty_long_prd)
    st.session_state.nifty_threshold = st.number_input("Nifty Signal Threshold (%)", min_value=0.0, value=st.session_state.nifty_threshold)
    st.session_state.nifty_sl_amount = st.number_input("Nifty Stop Loss (₹)", min_value=0, value=st.session_state.nifty_sl_amount)
    st.session_state.nifty_trail_sl_percent = st.number_input("Nifty Trailing SL (%)", min_value=0, value=st.session_state.nifty_trail_sl_percent)

st.subheader("BankNifty 📈")
with st.expander("⚙️ BankNifty Settings"):
    st.session_state.banknifty_ma_length = st.number_input("BankNifty MA Length", min_value=1, value=st.session_state.banknifty_ma_length)
    st.session_state.banknifty_short_prd = st.number_input("BankNifty Short Period", min_value=1, value=st.session_state.banknifty_short_prd)
    st.session_state.banknifty_long_prd = st.number_input("BankNifty Long Period", min_value=1, value=st.session_state.banknifty_long_prd)
    st.session_state.banknifty_threshold = st.number_input("BankNifty Signal Threshold (%)", min_value=0.0, value=st.session_state.banknifty_threshold)
    st.session_state.banknifty_sl_amount = st.number_input("BankNifty Stop Loss (₹)", min_value=0, value=st.session_state.banknifty_sl_amount)
    st.session_state.banknifty_trail_sl_percent = st.number_input("BankNifty Trailing SL (%)", min_value=0, value=st.session_state.banknifty_trail_sl_percent)

st.header("🔄 Auto Trading & ⏱️ Backtesting")
run_backtest_button = st.button("Run Backtest", key="run_all")

if run_backtest_button:
    st.write("Generating and backtesting 5 years of historical data. This may take a while...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365) # 5 saal ka data
    
    df_nifty = get_historical_data("^NSEI", start_date, end_date)
    df_banknifty = get_historical_data("^NSEBANK", start_date, end_date)

    if df_nifty is not None and not df_nifty.empty:
        run_backtest('Nifty', df_nifty.copy(), st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold, st.session_state.nifty_sl_amount, st.session_state.nifty_trail_sl_percent)
    else:
        st.error("Nifty data download karne mein error hua.")

    st.write("---")

    if df_banknifty is not None and not df_banknifty.empty:
        run_backtest('BankNifty', df_banknifty.copy(), st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold, st.session_state.banknifty_sl_amount, st.session_state.banknifty_trail_sl_percent)
    else:
        st.error("BankNifty data download karne mein error hua.")

 streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import pytz
import plotly.graph_objects as go
import json
import os

# --- Page Setup ---
st.set_page_config(page_title="Nifty & BankNifty Dashboard", layout="wide")
st.title("📊 Nifty & BankNifty Strategy Dashboard")

# --- Function to save settings ---
def save_settings(ma_length, short_prd, long_prd, threshold, sl_amount, trail_sl_percent, name):
    settings = {
        "ma_length": ma_length,
        "short_prd": short_prd,
        "long_prd": long_prd,
        "threshold": threshold,
        "sl_amount": sl_amount,
        "trail_sl_percent": trail_sl_percent
    }
    with open(f"settings_{name}.json", "w") as f:
        json.dump(settings, f)
    st.success(f"Settings for {name} saved successfully!")

# --- Function to load settings ---
def load_settings(name):
    if os.path.exists(f"settings_{name}.json"):
        with open(f"settings_{name}.json", "r") as f:
            settings = json.load(f)
        return settings
    return None

# --- Persistent Strategy Settings (with load on startup) ---
nifty_settings = load_settings("nifty")
if "nifty_ma_length" not in st.session_state:
    st.session_state.nifty_ma_length = nifty_settings["ma_length"] if nifty_settings else 20
if "nifty_short_prd" not in st.session_state:
    st.session_state.nifty_short_prd = nifty_settings["short_prd"] if nifty_settings else 3
if "nifty_long_prd" not in st.session_state:
    st.session_state.nifty_long_prd = nifty_settings["long_prd"] if nifty_settings else 6
if "nifty_threshold" not in st.session_state:
    st.session_state.nifty_threshold = nifty_settings["threshold"] if nifty_settings else 1.5
if "nifty_sl_amount" not in st.session_state:
    st.session_state.nifty_sl_amount = nifty_settings["sl_amount"] if nifty_settings and "sl_amount" in nifty_settings else 600
if "nifty_trail_sl_percent" not in st.session_state:
    st.session_state.nifty_trail_sl_percent = nifty_settings["trail_sl_percent"] if nifty_settings and "trail_sl_percent" in nifty_settings else 0.5

banknifty_settings = load_settings("banknifty")
if "banknifty_ma_length" not in st.session_state:
    st.session_state.banknifty_ma_length = banknifty_settings["ma_length"] if banknifty_settings else 20
if "banknifty_short_prd" not in st.session_state:
    st.session_state.banknifty_short_prd = banknifty_settings["short_prd"] if banknifty_settings else 3
if "banknifty_long_prd" not in st.session_state:
    st.session_state.banknifty_long_prd = banknifty_settings["long_prd"] if banknifty_settings else 6
if "banknifty_threshold" not in st.session_state:
    st.session_state.banknifty_threshold = banknifty_settings["threshold"] if banknifty_settings else 1.5
if "banknifty_sl_amount" not in st.session_state:
    st.session_state.banknifty_sl_amount = banknifty_settings["sl_amount"] if banknifty_settings and "sl_amount" in banknifty_settings else 600
if "banknifty_trail_sl_percent" not in st.session_state:
    st.session_state.banknifty_trail_sl_percent = banknifty_settings["trail_sl_percent"] if banknifty_settings and "trail_sl_percent" in banknifty_settings else 0.5

if "trade_logs" not in st.session_state:
    st.session_state.trade_logs = []
if "open_nifty_trade" not in st.session_state:
    st.session_state.open_nifty_trade = None
if "open_banknifty_trade" not in st.session_state:
    st.session_state.open_banknifty_trade = None

# New state to hold backtest data for charts
if "backtest_data" not in st.session_state:
    st.session_state.backtest_data = None

# --- Sample Data Generator for 5 years ---
def generate_sample_data(index_name, historical=False):
    np.random.seed(42)
    if historical:
        start_time = datetime.now() - timedelta(days=5*365)
        end_time = datetime.now()
    else:
        start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
    
    time_diff = end_time - start_time
    num_periods = int(time_diff.total_seconds() / 300)
    dates = pd.date_range(start=start_time, periods=num_periods, freq='5min')
    
    if index_name == 'Nifty':
        initial_price = 19500
        volatility = 20
    else:
        initial_price = 45000
        volatility = 50
        
    prices = initial_price + np.cumsum(np.random.randn(num_periods) * volatility)
    return pd.DataFrame({'Date': dates, 'Close': prices})

# --- Signal Logic (based on crossover) ---
def get_trade_signal(current_disparity, current_disparity_ma, prev_disparity, prev_disparity_ma, threshold):
    if prev_disparity < prev_disparity_ma and current_disparity > current_disparity_ma:
        if current_disparity > threshold:
            return "Buy PE"
    elif prev_disparity > prev_disparity_ma and current_disparity < current_disparity_ma:
        if current_disparity < -threshold:
            return "Buy CE"
    return None

# --- Full Backtest Function (Updated Logic) ---
def run_backtest(index_name, df, ma_length, short_prd, long_prd, threshold, sl_amount, trail_sl_percent):
    
    df['MA'] = df['Close'].rolling(window=ma_length).mean()
    df['Disparity'] = (df['Close'] - df['MA']) / df['MA'] * 100
    df['Disparity_MA'] = df['Disparity'].rolling(window=short_prd).mean()
    df.dropna(inplace=True)

    open_trade = None
    for i in range(1, len(df)):
        current_row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # --- NEW: Filter by Indian market hours (9:15 AM to 3:30 PM) ---
        market_start = time(9, 15)
        market_end = time(15, 30)
        
        current_time = current_row['Date'].time()
        
        if not (market_start <= current_time <= market_end):
            # If a trade is open and market closes, close it
            if open_trade:
                pnl = 0
                if open_trade['signal'] == "Buy CE":
                    pnl = current_row['Close'] - open_trade['price']
                elif open_trade['signal'] == "Buy PE":
                    pnl = open_trade['price'] - current_row['price']
                
                st.session_state.trade_logs.append({
                    "Index": index_name,
                    "Timestamp": current_row['Date'],
                    "Date": current_row['Date'].strftime("%Y-%m-%d"),
                    "Month": current_row['Date'].strftime("%Y-%m"),
                    "Trade": open_trade['signal'],
                    "Entry/Exit": "Exit",
                    "Reason": "Market Close",
                    "Price": round(current_row['Close'], 2),
                    "P&L": round(pnl, 2)
                })
                open_trade = None
            continue # Skip to the next data point

        signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], threshold)
        
        # Check for open trade and update trailing SL or exit
        if open_trade:
            # Update the peak/lowest price for trailing stop-loss
            if open_trade['signal'] == "Buy CE":
                open_trade['peak_price'] = max(open_trade['peak_price'], current_row['Close'])
                sl_level = open_trade['peak_price'] - (open_trade['peak_price'] * trail_sl_percent / 100)
                pnl = current_row['Close'] - open_trade['price']
                
                if current_row['Close'] <= sl_level:
                    st.session_state.trade_logs.append({
                        "Index": index_name,
                        "Timestamp": current_row['Date'],
                        "Date": current_row['Date'].strftime("%Y-%m-%d"),
                        "Month": current_row['Date'].strftime("%Y-%m"),
                        "Trade": open_trade['signal'],
                        "Entry/Exit": "Exit",
                        "Reason": "Trailing SL",
                        "Price": round(current_row['Close'], 2),
                        "P&L": round(pnl, 2)
                    })
                    open_trade = None
            elif open_trade['signal'] == "Buy PE":
                open_trade['lowest_price'] = min(open_trade['lowest_price'], current_row['Close'])
                sl_level = open_trade['lowest_price'] + (open_trade['lowest_price'] * trail_sl_percent / 100)
                pnl = open_trade['price'] - current_row['Close']
                
                if current_row['Close'] >= sl_level:
                    st.session_state.trade_logs.append({
                        "Index": index_name,
                        "Timestamp": current_row['Date'],
                        "Date": current_row['Date'].strftime("%Y-%m-%d"),
                        "Month": current_row['Date'].strftime("%Y-%m"),
                        "Trade": open_trade['signal'],
                        "Entry/Exit": "Exit",
                        "Reason": "Trailing SL",
                        "Price": round(current_row['Close'], 2),
                        "P&L": round(pnl, 2)
                    })
                    open_trade = None
            
            # Check for fixed stop-loss and crossover exit (if not already exited by trailing SL)
            if open_trade:
                if pnl <= -sl_amount:
                    st.session_state.trade_logs.append({
                        "Index": index_name,
                        "Timestamp": current_row['Date'],
                        "Date": current_row['Date'].strftime("%Y-%m-%d"),
                        "Month": current_row['Date'].strftime("%Y-%m"),
                        "Trade": open_trade['signal'],
                        "Entry/Exit": "Exit",
                        "Reason": "Stop Loss",
                        "Price": round(current_row['Close'], 2),
                        "P&L": round(pnl, 2)
                    })
                    open_trade = None
                elif signal and open_trade['signal'] != signal:
                    st.session_state.trade_logs.append({
                        "Index": index_name,
                        "Timestamp": current_row['Date'],
                        "Date": current_row['Date'].strftime("%Y-%m-%d"),
                        "Month": current_row['Date'].strftime("%Y-%m"),
                        "Trade": open_trade['signal'],
                        "Entry/Exit": "Exit",
                        "Reason": "Crossover Signal",
                        "Price": round(current_row['Close'], 2),
                        "P&L": round(pnl, 2)
                    })
                    open_trade = None

        # Check for entry condition
        elif not open_trade and signal:
            st.session_state.trade_logs.append({
                "Index": index_name,
                "Timestamp": current_row['Date'],
                "Date": current_row['Date'].strftime("%Y-%m-%d"),
                "Month": current_row['Date'].strftime("%Y-%m"),
                "Trade": signal,
                "Entry/Exit": "Entry",
                "Reason": "Crossover Signal",
                "Price": round(current_row['Close'], 2),
                "P&L": 0
            })
            open_trade = {
                "signal": signal,
                "price": current_row['Close'],
                "peak_price": current_row['Close'],
                "lowest_price": current_row['Close']
            }


# --- Create two columns for side-by-side display ---
col1, col2 = st.columns(2)

with col1:
    st.header("Nifty 📈")
    st.subheader("⚙️ Nifty Settings")
    st.session_state.nifty_ma_length = st.number_input("Nifty MA Length", min_value=1, max_value=50, value=st.session_state.nifty_ma_length, key="nifty_ma_length_input")
    st.session_state.nifty_short_prd = st.number_input("Nifty Short Period", min_value=1, max_value=20, value=st.session_state.nifty_short_prd, key="nifty_short_prd_input")
    st.session_state.nifty_long_prd = st.number_input("Nifty Long Period", min_value=1, max_value=50, value=st.session_state.nifty_long_prd, key="nifty_long_prd_input")
    st.session_state.nifty_threshold = st.slider("Nifty Signal Threshold (%)", min_value=0.5, max_value=5.0, value=st.session_state.nifty_threshold, step=0.1, key="nifty_threshold_slider")
    st.session_state.nifty_sl_amount = st.number_input("Nifty Stop Loss (₹)", min_value=100, max_value=5000, value=st.session_state.nifty_sl_amount, step=50, key="nifty_sl_amount_input")
    st.session_state.nifty_trail_sl_percent = st.slider("Nifty Trailing SL (%)", min_value=0.1, max_value=5.0, value=st.session_state.nifty_trail_sl_percent, step=0.1, key="nifty_trail_sl_percent_input")


    if st.button("💾 Save Nifty Settings", key="nifty_save_button"):
        save_settings(st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold, st.session_state.nifty_sl_amount, st.session_state.nifty_trail_sl_percent, "nifty")

with col2:
    st.header("BankNifty 📈")
    st.subheader("⚙️ BankNifty Settings")
    st.session_state.banknifty_ma_length = st.number_input("BankNifty MA Length", min_value=1, max_value=50, value=st.session_state.banknifty_ma_length, key="banknifty_ma_length_input")
    st.session_state.banknifty_short_prd = st.number_input("BankNifty Short Period", min_value=1, max_value=20, value=st.session_state.banknifty_short_prd, key="banknifty_short_prd_input")
    st.session_state.banknifty_long_prd = st.number_input("BankNifty Long Period", min_value=1, max_value=50, value=st.session_state.banknifty_long_prd, key="banknifty_long_prd_input")
    st.session_state.banknifty_threshold = st.slider("BankNifty Signal Threshold (%)", min_value=0.5, max_value=5.0, value=st.session_state.banknifty_threshold, step=0.1, key="banknifty_threshold_slider")
    st.session_state.banknifty_sl_amount = st.number_input("BankNifty Stop Loss (₹)", min_value=100, max_value=5000, value=st.session_state.banknifty_sl_amount, step=50, key="banknifty_sl_amount_input")
    st.session_state.banknifty_trail_sl_percent = st.slider("BankNifty Trailing SL (%)", min_value=0.1, max_value=5.0, value=st.session_state.banknifty_trail_sl_percent, step=0.1, key="banknifty_trail_sl_percent_input")
    if st.button("💾 Save BankNifty Settings", key="banknifty_save_button"):
        save_settings(st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold, st.session_state.banknifty_sl_amount, st.session_state.banknifty_trail_sl_percent, "banknifty")

# --- Auto Trading & Backtesting section ---
st.markdown("---")
st.header("🔄 Auto Trading & ⏱️ Backtesting")

backtest_col, auto_col = st.columns(2)
with backtest_col:
    if st.button("▶️ Run 5-Year Backtest", key="run_backtest_button"):
        st.info("Generating and backtesting 5 years of historical data. This may take a while...")
        
        st.session_state.trade_logs = []
        
        # Generate and store data
        df_nifty = generate_sample_data('Nifty', historical=True)
        df_banknifty = generate_sample_data('BankNifty', historical=True)
        st.session_state.backtest_data = {
            'Nifty': df_nifty,
            'BankNifty': df_banknifty
        }

        # Run backtest with stored data
        run_backtest('Nifty', df_nifty.copy(), st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold, st.session_state.nifty_sl_amount, st.session_state.nifty_trail_sl_percent)
        run_backtest('BankNifty', df_banknifty.copy(), st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold, st.session_state.banknifty_sl_amount, st.session_state.banknifty_trail_sl_percent)
        st.success("Backtest completed! Results are shown below.")

with auto_col:
    auto_mode = st.toggle("🔄 Auto Strategy Mode (Live Data)", value=False)
    if auto_mode:
        st.warning("Auto Mode is not fully implemented for this version. Trade logs will show current time.")

# --- Display Charts ---
st.markdown("---")
st.header("📈 Disparity Index Charts")

# Use backtest data if available, otherwise use live-day data
if st.session_state.backtest_data:
    df_nifty_chart = st.session_state.backtest_data['Nifty'].copy()
    df_banknifty_chart = st.session_state.backtest_data['BankNifty'].copy()
    
else:
    df_nifty_chart = generate_sample_data('Nifty')
    df_banknifty_chart = generate_sample_data('BankNifty')


df_nifty_chart['MA'] = df_nifty_chart['Close'].rolling(window=st.session_state.nifty_ma_length).mean()
df_nifty_chart['Disparity'] = (df_nifty_chart['Close'] - df_nifty_chart['MA']) / df_nifty_chart['MA'] * 100
df_nifty_chart['Disparity_MA'] = df_nifty_chart['Disparity'].rolling(window=st.session_state.nifty_short_prd).mean()
df_nifty_chart.dropna(inplace=True)

df_banknifty_chart['MA'] = df_banknifty_chart['Close'].rolling(window=st.session_state.banknifty_ma_length).mean()
df_banknifty_chart['Disparity'] = (df_banknifty_chart['Close'] - df_banknifty_chart['MA']) / df_banknifty_chart['MA'] * 100
df_banknifty_chart['Disparity_MA'] = df_banknifty_chart['Disparity'].rolling(window=st.session_state.banknifty_short_prd).mean()
df_banknifty_chart.dropna(inplace=True)

fig_nifty = go.Figure()
fig_nifty.add_trace(go.Scatter(x=df_nifty_chart['Date'], y=df_nifty_chart['Disparity'], name='Disparity Index', line=dict(color='blue', width=2)))
fig_nifty.add_trace(go.Scatter(x=df_nifty_chart['Date'], y=df_nifty_chart['Disparity_MA'], name='Disparity MA', line=dict(color='green', width=2)))

fig_banknifty = go.Figure()
fig_banknifty.add_trace(go.Scatter(x=df_banknifty_chart['Date'], y=df_banknifty_chart['Disparity'], name='Disparity Index', line=dict(color='blue', width=2)))
fig_banknifty.add_trace(go.Scatter(x=df_banknifty_chart['Date'], y=df_banknifty_chart['Disparity_MA'], name='Disparity MA', line=dict(color='green', width=2)))

with col1:
    st.plotly_chart(fig_nifty, use_container_width=True)
with col2:
    st.plotly_chart(fig_banknifty, use_container_width=True)

# --- Backtest Results & P&L Analysis ---
st.markdown("---")
st.header("📊 Backtest Results & P&L Analysis")

if st.session_state.trade_logs:
    df_logs = pd.DataFrame(st.session_state.trade_logs)
    
    # Filter for completed trades (where P&L is not 0)
    completed_trades = df_logs[df_logs['P&L'] != 0].copy()
    
    # 1. Overall Backtest Results
    total_pnl = completed_trades["P&L"].sum()
    winning_trades = completed_trades[completed_trades["P&L"] > 0].shape[0]
    losing_trades = completed_trades[completed_trades["P&L"] < 0].shape[0]
    total_trades = len(completed_trades)
    
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    st.subheader("Strategy Performance Summary")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    
    kpi_col1.metric("Total P&L", f"₹{total_pnl:,.2f}")
    kpi_col2.metric("Total Trades", total_trades)
    kpi_col3.metric("Winning Trades", winning_trades)
    kpi_col4.metric("Losing Trades", losing_trades)
    kpi_col5.metric("Win Rate", f"{win_rate:,.2f}%")

    # 2. Daily P&L
    st.markdown("---")
    st.subheader("Daily P&L")
    daily_pnl = completed_trades.groupby("Date")["P&L"].sum().reset_index()
    daily_pnl.columns = ["Date", "Daily P&L"]
    st.dataframe(daily_pnl, use_container_width=True)

    # 3. Monthly P&L
    st.markdown("---")
    st.subheader("Monthly P&L")
    monthly_pnl = completed_trades.groupby("Month")["P&L"].sum().reset_index()
    monthly_pnl.columns = ["Month", "Monthly P&L"]
    st.dataframe(monthly_pnl, use_container_width=True)

    # 4. Detailed Trade Logs
    st.markdown("---")
    st.subheader("Detailed Trade Logs (All Entries and Exits)")
    df_logs['Timestamp'] = pd.to_datetime(df_logs['Timestamp'])
    df_logs = df_logs.sort_values(by='Timestamp', ascending=False)
    
    # Separate Nifty and BankNifty logs
    nifty_logs = df_logs[df_logs['Index'] == 'Nifty']
    banknifty_logs = df_logs[df_logs['Index'] == 'BankNifty']
    
    if not nifty_logs.empty:
        st.markdown("### Nifty Trade Logs")
        st.dataframe(nifty_logs, use_container_width=True)
    else:
        st.info("No Nifty trades logged.")
    
    if not banknifty_logs.empty:
        st.markdown("### BankNifty Trade Logs")
        st.dataframe(banknifty_logs, use_container_width=True)
    else:
        st.info("No BankNifty trades logged.")

else:
    st.info("📭 No trades logged yet. Click 'Run 5-Year Backtest' to see results.")
