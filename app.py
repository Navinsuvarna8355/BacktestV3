import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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
if "open_nifty_trade" not in st.session_state:
    st.session_state.open_nifty_trade = None
if "open_banknifty_trade" not in st.session_state:
    st.session_state.open_banknifty_trade = None

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

# --- Trade Logger for Live Data ---
def log_live_trade(signal, price, disparity, index_name):
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    pnl = 0
    trade_type = "Entry"
    
    # Live trade logic (simplified)
    if index_name == "Nifty" and st.session_state.open_nifty_trade:
        if st.session_state.open_nifty_trade['Trade'] != signal:
            trade_type = "Exit"
            if signal == "Buy PE":
                pnl = st.session_state.open_nifty_trade['Price'] - price
            else:
                pnl = price - st.session_state.open_nifty_trade['Price']
            st.session_state.open_nifty_trade = None
    elif index_name == "BankNifty" and st.session_state.open_banknifty_trade:
        if st.session_state.open_banknifty_trade['Trade'] != signal:
            trade_type = "Exit"
            if signal == "Buy PE":
                pnl = st.session_state.open_banknifty_trade['Price'] - price
            else:
                pnl = price - st.session_state.open_banknifty_trade['Price']
            st.session_state.open_banknifty_trade = None

    if trade_type == "Entry":
        if index_name == "Nifty":
            st.session_state.open_nifty_trade = {"Trade": signal, "Price": price}
        else:
            st.session_state.open_banknifty_trade = {"Trade": signal, "Price": price}

    st.session_state.trade_logs.append({
        "Index": index_name,
        "Timestamp": now,
        "Date": now.strftime("%Y-%m-%d"),
        "Month": now.strftime("%Y-%m"),
        "Trade": signal,
        "Entry/Exit": trade_type,
        "Price": round(price, 2),
        "P&L": round(pnl, 2)
    })
    
# --- Full Backtest Function ---
def run_backtest(index_name, df, ma_length, short_prd, long_prd, threshold):
    
    df['MA'] = df['Close'].rolling(window=ma_length).mean()
    df['Disparity'] = (df['Close'] - df['MA']) / df['MA'] * 100
    df['Disparity_MA'] = df['Disparity'].rolling(window=short_prd).mean()
    df.dropna(inplace=True)

    open_trade = None
    for i in range(1, len(df)):
        current_row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        signal = get_trade_signal(current_row['Disparity'], current_row['Disparity_MA'], prev_row['Disparity'], prev_row['Disparity_MA'], threshold)
        
        if signal:
            trade_type = "Entry"
            pnl = 0
            
            if open_trade and open_trade['signal'] != signal:
                if signal == "Buy PE" and open_trade['signal'] == "Buy CE":
                    pnl = open_trade['price'] - current_row['Close']
                elif signal == "Buy CE" and open_trade['signal'] == "Buy PE":
                    pnl = current_row['Close'] - open_trade['price']
                trade_type = "Exit"
                
                # Log the exit
                st.session_state.trade_logs.append({
                    "Index": index_name,
                    "Timestamp": current_row['Date'],  # FIXED: Use the historical date
                    "Date": current_row['Date'].strftime("%Y-%m-%d"),
                    "Month": current_row['Date'].strftime("%Y-%m"),
                    "Trade": signal,
                    "Entry/Exit": trade_type,
                    "Price": round(current_row['Close'], 2),
                    "P&L": round(pnl, 2)
                })
                open_trade = None
            
            if not open_trade:
                # Log the entry
                st.session_state.trade_logs.append({
                    "Index": index_name,
                    "Timestamp": current_row['Date'],  # FIXED: Use the historical date
                    "Date": current_row['Date'].strftime("%Y-%m-%d"),
                    "Month": current_row['Date'].strftime("%Y-%m"),
                    "Trade": signal,
                    "Entry/Exit": "Entry",
                    "Price": round(current_row['Close'], 2),
                    "P&L": 0
                })
                open_trade = {
                    "signal": signal,
                    "price": current_row['Close']
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
    if st.button("▶️ Run 5-Year Backtest", key="run_backtest_button"):
        st.info("Generating and backtesting 5 years of historical data. This may take a while...")
        
        st.session_state.trade_logs = []
        
        # Nifty Backtest
        df_nifty = generate_sample_data('Nifty', historical=True)
        run_backtest('Nifty', df_nifty, st.session_state.nifty_ma_length, st.session_state.nifty_short_prd, st.session_state.nifty_long_prd, st.session_state.nifty_threshold)
        
        # BankNifty Backtest
        df_banknifty = generate_sample_data('BankNifty', historical=True)
        run_backtest('BankNifty', df_banknifty, st.session_state.banknifty_ma_length, st.session_state.banknifty_short_prd, st.session_state.banknifty_long_prd, st.session_state.banknifty_threshold)
        st.success("Backtest completed! Results are shown below.")

with auto_col:
    auto_mode = st.toggle("🔄 Auto Strategy Mode (Live Data)", value=False)
    if auto_mode:
        st.warning("Auto Mode is not fully implemented for this version. Trade logs will show current time.")

# --- Display Charts (Using the current day's data) ---
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
