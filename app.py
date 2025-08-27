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

