import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz
import plotly.graph_objects as go
import json
import os

# --- Page Setup ---
st.set_page_config(page_title="Nifty & BankNifty Dashboard", layout="wide")
st.title("📊 Nifty & BankNifty Strategy Dashboard")

# --- Function to save settings ---
def save_settings(ma_length, short_prd, long_prd, threshold, name):
    settings = {
        "ma_length": ma_length,
        "short_prd": short_prd,
        "long_prd": long_prd,
        "threshold": threshold
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

banknifty_settings = load_settings("banknifty")
if "banknifty_ma_length" not in st.session_state:
    st.session_state.banknifty_ma_length = banknifty_settings["ma_length"] if banknifty_settings else 20
if "banknifty_short_prd" not in st.session_state:
    st.session_state.banknifty_short_prd = banknifty_settings["short_prd"] if banknifty_settings else 3
if "banknifty_long_prd" not in st.session_state:
    st.session_state.banknifty_long_prd = banknifty_settings["long_prd"] if banknifty_settings else 6
if "banknifty_threshold" not in st.session_state:
    st.session_state.banknifty_threshold = banknifty_settings["threshold"] if banknifty_settings else 1.5

if "trade_logs" not in st.session_state:
    st.session_state.trade_logs = []

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

# --- Trade Logger with P&L ---
def log_trade(signal, price, disparity, index_name):
    # Simulate a P&L for demonstration purposes
    pnl = round(np.random.uniform(-500, 1000), 2)  # Random P&L between -500 and +1000
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    st.session_state.trade_logs.append({
        "Index": index_name,
        "Timestamp": now,
        "Date": now.strftime("%Y-%m-%d"),
        "Month": now.strftime("%Y-%m"),
        "Trade": signal,
        "Price": round(price, 2),
        "Disparity": round(disparity, 2),
        "P&L": pnl
    })
    
# --- Create two columns for side-by-side display ---
col1, col2 = st.columns(2)

with col1:
    st.header("Nifty 📈")
    st.subheader("⚙️ Nifty Settings")
    st.session_state.nifty_ma_length = st.number_input("Nifty MA Length", min_value=1, max_value=50, value=st.session_state.nifty_ma_length, key="nifty_ma_length_input")
    st.session_state.nifty_short_prd = st.number_input("Nifty Short Period", min_value=1, max_value=20, value=st.session_state.nifty_short_prd, key="nifty_short_prd_input")
    st.session_state.nifty_long_prd = st.number_input("Nifty Long Period", min_value=1, max_value=50, value=st.session_state.nifty_long_prd, key="nifty_long_prd_input")
    st.session_state.nifty_threshold = st.slider("Nifty Signal Threshold (%)", min_value=0.5, max_value=5.0, value=st.session_state.nifty_threshold, step=0.1, key="nifty_threshold_slider")
    if st.button("💾 Save Nifty Settings", key="nifty_save_button"):
        save_settings(st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold, "nifty")

with col2:
    st.header("BankNifty 📈")
    st.subheader("⚙️ BankNifty Settings")
    st.session_state.banknifty_ma_length = st.number_input("BankNifty MA Length", min_value=1, max_value=50, value=st.session_state.banknifty_ma_length, key="banknifty_ma_length_input")
    st.session_state.banknifty_short_prd = st.number_input("BankNifty Short Period", min_value=1, max_value=20, value=st.session_state.banknifty_short_prd, key="banknifty_short_prd_input")
    st.session_state.banknifty_long_prd = st.number_input("BankNifty Long Period", min_value=1, max_value=50, value=st.session_state.banknifty_long_prd, key="banknifty_long_prd_input")
    st.session_state.banknifty_threshold = st.slider("BankNifty Signal Threshold (%)", min_value=0.5, max_value=5.0, value=st.session_state.banknifty_threshold, step=0.1, key="banknifty_threshold_slider")
    if st.button("💾 Save BankNifty Settings", key="banknifty_save_button"):
        save_settings(st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold, "banknifty")

# --- Auto Trading & Backtesting section ---
st.markdown("---")
st.header("🔄 Auto Trading & ⏱️ Backtesting")

backtest_col, auto_col = st.columns(2)
with backtest_col:
    backtest_button = st.button("▶️ Run 5-Year Backtest", key="run_backtest_button")
with auto_col:
    auto_mode = st.toggle("🔄 Auto Strategy Mode (Live Data)", value=False)


# --- Determine which data to use based on the button/toggle ---
if backtest_button:
    st.info("Generating 5 years of historical data. This may take a moment...")
    df_nifty = generate_sample_data('Nifty', historical=True)
    df_banknifty = generate_sample_data('BankNifty', historical=True)
    st.session_state.trade_logs = []
    
    # Apply strategy logic to historical data
    df_nifty['MA'] = df_nifty['Close'].rolling(window=st.session_state.nifty_ma_length).mean()
    df_nifty['Disparity'] = (df_nifty['Close'] - df_nifty['MA']) / df_nifty['MA'] * 100
    df_nifty['Disparity_MA'] = df_nifty['Disparity'].rolling(window=st.session_state.nifty_short_prd).mean()
    df_nifty.dropna(inplace=True)
    
    df_banknifty['MA'] = df_banknifty['Close'].rolling(window=st.session_state.banknifty_ma_length).mean()
    df_banknifty['Disparity'] = (df_banknifty['Close'] - df_banknifty['MA']) / df_banknifty['MA'] * 100
    df_banknifty['Disparity_MA'] = df_banknifty['Disparity'].rolling(window=st.session_state.banknifty_short_prd).mean()
    df_banknifty.dropna(inplace=True)

    # Nifty Backtest
    for i in range(1, len(df_nifty)):
        current_row = df_nifty.iloc[i]
        prev_row = df_nifty.iloc[i-1]
        nifty_signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], st.session_state.nifty_threshold)
        if nifty_signal:
            log_trade(nifty_signal, current_row['Close'], current_row['Disparity'], 'Nifty')
    st.success("Nifty backtest completed!")
    
    # BankNifty Backtest
    for i in range(1, len(df_banknifty)):
        current_row = df_banknifty.iloc[i]
        prev_row = df_banknifty.iloc[i-1]
        banknifty_signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], st.session_state.banknifty_threshold)
        if banknifty_signal:
            log_trade(banknifty_signal, current_row['Close'], current_row['Disparity'], 'BankNifty')
    st.success("BankNifty backtest completed!")

# --- Auto Trading Logic ---
if auto_mode:
    df_nifty = generate_sample_data('Nifty')
    df_banknifty = generate_sample_data('BankNifty')

    df_nifty['MA'] = df_nifty['Close'].rolling(window=st.session_state.nifty_ma_length).mean()
    df_nifty['Disparity'] = (df_nifty['Close'] - df_nifty['MA']) / df_nifty['MA'] * 100
    df_nifty['Disparity_MA'] = df_nifty['Disparity'].rolling(window=st.session_state.nifty_short_prd).mean()
    df_nifty.dropna(inplace=True)
    
    df_banknifty['MA'] = df_banknifty['Close'].rolling(window=st.session_state.banknifty_ma_length).mean()
    df_banknifty['Disparity'] = (df_banknifty['Close'] - df_banknifty['MA']) / df_banknifty['MA'] * 100
    df_banknifty['Disparity_MA'] = df_banknifty['Disparity'].rolling(window=st.session_state.banknifty_short_prd).mean()
    df_banknifty.dropna(inplace=True)

    # Nifty Crossover Check
    if len(df_nifty) >= 2:
        prev_row = df_nifty.iloc[-2]
        current_row = df_nifty.iloc[-1]
        nifty_signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], st.session_state.nifty_threshold)
        if nifty_signal:
            log_trade(nifty_signal, current_row['Close'], current_row['Disparity'], 'Nifty')
            st.success(f"✅ Nifty Trade: {nifty_signal} @ {current_row['Close']:.2f}")

    # BankNifty Crossover Check
    if len(df_banknifty) >= 2:
        prev_row = df_banknifty.iloc[-2]
        current_row = df_banknifty.iloc[-1]
        banknifty_signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], st.session_state.banknifty_threshold)
        if banknifty_signal:
            log_trade(banknifty_signal, current_row['Close'], current_row['Disparity'], 'BankNifty')
            st.success(f"✅ BankNifty Trade: {banknifty_signal} @ {current_row['Close']:.2f}")

    if not st.session_state.trade_logs:
        st.info("No trade signal at this moment.")

# --- Display Charts (Using the current data) ---
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
    df_logs["Timestamp"] = pd.to_datetime(df_logs["Timestamp"])
    
    # 1. Overall Backtest Results
    total_pnl = df_logs["P&L"].sum()
    winning_trades = df_logs[df_logs["P&L"] > 0].shape[0]
    losing_trades = df_logs[df_logs["P&L"] < 0].shape[0]
    total_trades = len(df_logs)
    
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    total_profit = df_logs[df_logs["P&L"] > 0]["P&L"].sum()
    total_loss = df_logs[df_logs["P&L"] < 0]["P&L"].sum()

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
    daily_pnl = df_logs.groupby("Date")["P&L"].sum().reset_index()
    daily_pnl["Date"] = pd.to_datetime(daily_pnl["Date"]).dt.date
    st.dataframe(daily_pnl, use_container_width=True)

    # 3. Monthly P&L
    st.markdown("---")
    st.subheader("Monthly P&L")
    monthly_pnl = df_logs.groupby("Month")["P&L"].sum().reset_index()
    st.dataframe(monthly_pnl, use_container_width=True)

    # 4. Detailed Trade Logs
    st.markdown("---")
    st.subheader("Detailed Trade Logs")
    st.dataframe(df_logs, use_container_width=True)
else:
    st.info("📭 No trades logged yet. Click 'Run 5-Year Backtest' or toggle 'Auto Strategy Mode' to begin.")
