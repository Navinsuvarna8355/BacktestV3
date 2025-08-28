# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="Nifty & BankNifty Strategy Dashboard")

st.title("📊 Nifty & BankNifty Strategy Dashboard")
st.write("Disparity Index strategy ke saath Nifty aur BankNifty backtest karein.")

# --- Session State Initialization ---
def init_session_state():
    """Session state variables ko initialize karta hai."""
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

# --- Data Functions ---
@st.cache_data
def get_historical_data(symbol, start_date, end_date):
    """
    Yahoo Finance se historical data download karta hai.
    Puraane "yf.download" method ko naye aur behtar "yf.Ticker().history" se badla gaya hai.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        
        if data.empty:
            st.warning(f"{symbol} ka data nahi mila. Kripya symbol aur time range check karein.")
            return None
        return data
    except Exception as e:
        st.error(f"Historical data download karne mein error: {e}. Kripya sahi symbol check karein.")
        return None

def calculate_indicators(df, params):
    """Dataframe par indicators calculate karta hai."""
    if df is None or df.empty:
        return None
    
    df_copy = df.copy()
    
    # Extra columns jaise ki 'Adj Close' ko drop karte hain jo error de sakte hain
    if 'Adj Close' in df_copy.columns:
        df_copy.drop(columns=['Adj Close'], inplace=True)
    
    # ensure that the close column is present before calculation
    if 'Close' not in df_copy.columns:
        st.error("Data mein 'Close' column nahi mila. Calculation sambhav nahi hai.")
        return None

    try:
        # EMA calculate karte hain
        ema_series = df_copy['Close'].ewm(span=params['ma_length'], adjust=False).mean()
        df_copy['EMA_Length'] = ema_series
        
        # Disparity Index (DI) ko step-by-step calculate karte hain
        di_series = ((df_copy['Close'] - df_copy['EMA_Length']) / df_copy['EMA_Length']) * 100
        df_copy['DI'] = di_series
        
        # HSP short aur long period calculate karte hain
        hsp_short_series = df_copy['DI'].ewm(span=params['short_prd'], adjust=False).mean()
        df_copy['hsp_short'] = hsp_short_series
        
        hsp_long_series = df_copy['DI'].ewm(span=params['long_prd'], adjust=False).mean()
        df_copy['hsp_long'] = hsp_long_series
        
        # Final NaN values ko drop karte hain
        df_copy.dropna(inplace=True)
        
    except Exception as e:
        st.error(f"Indicators calculate karne mein error hua: {e}. Kripya parameters check karein.")
        return None
    
    return df_copy

# --- Trade Log Split ---
def split_trade_log(trade_log):
    """Trade log ko daily aur monthly summary mein split karta hai."""
    df_log = pd.DataFrame(trade_log)
    if df_log.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    df_log['buy_date'] = pd.to_datetime(df_log['buy_date'])
    df_log['month'] = df_log['buy_date'].dt.to_period('M')
    df_log['day'] = df_log['buy_date'].dt.date
    
    daily_log = df_log.groupby('day').agg({'pnl': 'sum', 'buy_price': 'count'}).rename(columns={'buy_price': 'trades'})
    monthly_log = df_log.groupby('month').agg({'pnl': 'sum', 'buy_price': 'count'}).rename(columns={'buy_price': 'trades'})
    
    return df_log, daily_log, monthly_log

# --- Backtest Logic ---
def run_backtest_logic(index_name, df, params):
    """Diye gaye parameters ke hisab se backtest run karta hai."""
    if df is None or df.empty:
        st.warning(f"{index_name} ka backtest nahi chal paya kyuki data available nahi hai.")
        return

    st.write(f"📈 **{index_name} Backtest Results**")
    
    initial_capital = 100000
    trade_log = []
    in_trade = False
    open_trade = {}
    
    for i, (index, row) in enumerate(df.iterrows()):
        if in_trade:
            # Absolute Stop Loss logic
            if (row['Close'] - open_trade['buy_price']) < -params['sl_amount']:
                trade_log.append({
                    'buy_date': open_trade['buy_date'],
                    'buy_price': open_trade['buy_price'],
                    'sell_date': index.strftime('%Y-%m-%d'),
                    'sell_price': row['Close'],
                    'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital / open_trade['buy_price'])
                })
                in_trade = False
                open_trade = {}
                continue

        # Buy Signal
        if row['hsp_short'] > row['hsp_long'] and not in_trade and (row['hsp_short'] - row['hsp_long']) >= params['threshold']:
            open_trade = {'buy_date': index.strftime('%Y-%m-%d'), 'buy_price': row['Close'], 'signal_type': 'Buy'}
            trade_log.append(open_trade)
            in_trade = True
        
        # Sell Signal
        elif row['hsp_short'] < row['hsp_long'] and in_trade:
            trade_log.append({
                'sell_date': index.strftime('%Y-%m-%d'),
                'sell_price': row['Close'],
                'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital / open_trade['buy_price'])
            })
            in_trade = False
            open_trade = {}
    
    # Final Backtest Report
    final_pnl = sum(trade['pnl'] for trade in trade_log if 'pnl' in trade)
    total_return = (final_pnl / initial_capital) * 100

    st.subheader("Final Backtest Report")
    col1, col2, col3 = st.columns(3)
    col1.metric("Initial Capital", f"₹{initial_capital:.2f}")
    col2.metric("Total P&L", f"₹{final_pnl:.2f}")
    col3.metric("Total Return", f"{total_return:.2f}%")
    st.metric("Total Trades", len([t for t in trade_log if 'pnl' in t]))

    if [t for t in trade_log if 'pnl' in t]:
        df_log = pd.DataFrame([t for t in trade_log if 'pnl' in t])
        
        st.subheader("📜 Trade History")
        st.dataframe(df_log)
        
        _, daily_log, monthly_log = split_trade_log(df_log)
        
        st.subheader("📅 Daily Summary")
        st.dataframe(daily_log)

        st.subheader("🗓️ Monthly Summary")
        st.dataframe(monthly_log)
    else:
        st.write("Is strategy ke liye koi trade nahi mila.")

# --- Charting Logic ---
def plot_chart(df, title):
    """Candlestick chart par buy/sell signals plot karta hai."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        row_heights=[0.7, 0.3], subplot_titles=(f"{title} Price Chart", "Disparity Index"))
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'],
                                 high=df['High'],
                                 low=df['Low'],
                                 close=df['Close'],
                                 name='Price'),
                  row=1, col=1)
    
    # Buy Signals (upward arrows)
    buy_signals = df[df['hsp_short'] > df['hsp_long']]
    buy_signals = buy_signals[buy_signals['hsp_short'] - buy_signals['hsp_long'] >= 0.5]
    if not buy_signals.empty:
      fig.add_trace(go.Scatter(x=buy_signals.index,
                               y=buy_signals['Close'],
                               mode='markers',
                               marker_symbol='triangle-up',
                               marker_color='green',
                               marker_size=10,
                               name='Buy Signal'),
                    row=1, col=1)

    # Sell Signals (downward arrows)
    sell_signals = df[df['hsp_short'] < df['hsp_long']]
    if not sell_signals.empty:
      fig.add_trace(go.Scatter(x=sell_signals.index,
                               y=sell_signals['Close'],
                               mode='markers',
                               marker_symbol='triangle-down',
                               marker_color='red',
                               marker_size=10,
                               name='Sell Signal'),
                    row=1, col=1)
    
    # DI aur HSP chart
    fig.add_trace(go.Scatter(x=df.index, y=df['DI'], name='DI', line=dict(color='orange')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['hsp_short'], name='HSP Short', line=dict(color='blue')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['hsp_long'], name='HSP Long', line=dict(color='red')), row=2, col=1)
    
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)


# --- UI Config Inputs ---
st.subheader("Nifty 📈")
with st.expander("⚙️ Nifty Settings"):
    st.session_state.nifty_params['ma_length'] = st.number_input("Nifty MA Length", min_value=1, value=st.session_state.nifty_params['ma_length'], key="nifty_ma")
    st.session_state.nifty_params['short_prd'] = st.number_input("Nifty Short Period", min_value=1, value=st.session_state.nifty_params['short_prd'], key="nifty_short")
    st.session_state.nifty_params['long_prd'] = st.number_input("Nifty Long Period", min_value=1, value=st.session_state.nifty_params['long_prd'], key="nifty_long")
    st.session_state.nifty_params['threshold'] = st.number_input("Nifty Signal Threshold (%)", min_value=0.0, value=st.session_state.nifty_params['threshold'], key="nifty_threshold")
    st.session_state.nifty_params['sl_amount'] = st.number_input("Nifty Stop Loss (₹)", min_value=0, value=st.session_state.nifty_params['sl_amount'], key="nifty_sl")

st.subheader("BankNifty 📈")
with st.expander("⚙️ BankNifty Settings"):
    st.session_state.banknifty_params['ma_length'] = st.number_input("BankNifty MA Length", min_value=1, value=st.session_state.banknifty_params['ma_length'], key="banknifty_ma")
    st.session_state.banknifty_params['short_prd'] = st.number_input("BankNifty Short Period", min_value=1, value=st.session_state.banknifty_params['short_prd'], key="banknifty_short")
    st.session_state.banknifty_params['long_prd'] = st.number_input("BankNifty Long Period", min_value=1, value=st.session_state.banknifty_params['long_prd'], key="banknifty_long")
    st.session_state.banknifty_params['threshold'] = st.number_input("BankNifty Signal Threshold (%)", min_value=0.0, value=st.session_state.banknifty_params['threshold'], key="banknifty_threshold")
    st.session_state.banknifty_params['sl_amount'] = st.number_input("BankNifty Stop Loss (₹)", min_value=0, value=st.session_state.banknifty_params['sl_amount'], key="banknifty_sl")

# --- Main Execution ---
st.header("🔄 Auto Trading & ⏱️ Backtesting")
run_backtest_button = st.button("Run Backtest", key="run_all")
run_5_backtests_button = st.button("Run 5 Years 5 Backtest", key="run_5_backtests")

if run_backtest_button:
    st.write("Generating and backtesting 5 years of historical data. This may take a while...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)
    
    df_nifty = get_historical_data("^NSEI", start_date, end_date)
    df_banknifty = get_historical_data("^NSEBANK", start_date, end_date)

    if df_nifty is not None and not df_nifty.empty:
        df_nifty_calculated = calculate_indicators(df_nifty, st.session_state.nifty_params)
        if df_nifty_calculated is not None:
            run_backtest_logic('Nifty', df_nifty_calculated, st.session_state.nifty_params)
            plot_chart(df_nifty_calculated, 'Nifty 50')
    else:
        st.error("Nifty data download karne mein error hua ya data empty hai.")

    st.write("---")

    if df_banknifty is not None and not df_banknifty.empty:
        df_banknifty_calculated = calculate_indicators(df_banknifty, st.session_state.banknifty_params)
        if df_banknifty_calculated is not None:
            run_backtest_logic('BankNifty', df_banknifty_calculated, st.session_state.banknifty_params)
            plot_chart(df_banknifty_calculated, 'BankNifty')
    else:
        st.error("BankNifty data download karne mein error hua ya data empty hai.")

if run_5_backtests_button:
    st.write("Starting 5 consecutive backtests for Nifty and BankNifty...")
    
    for i in range(5):
        st.subheader(f"🔄 Backtest Run {i+1} (5 Years)")
        end_date = datetime.now() - timedelta(days=i * 365)
        start_date = end_date - timedelta(days=5 * 365)
        
        df_nifty = get_historical_data("^NSEI", start_date, end_date)
        df_banknifty = get_historical_data("^NSEBANK", start_date, end_date)
        
        if df_nifty is not None and not df_nifty.empty:
            df_nifty_calculated = calculate_indicators(df_nifty, st.session_state.nifty_params)
            if df_nifty_calculated is not None:
                run_backtest_logic(f'Nifty - Run {i+1}', df_nifty_calculated, st.session_state.nifty_params)
                
        st.write("---")
        
        if df_banknifty is not None and not df_banknifty.empty:
            df_banknifty_calculated = calculate_indicators(df_banknifty, st.session_state.banknifty_params)
            if df_banknifty_calculated is not None:
                run_backtest_logic(f'BankNifty - Run {i+1}', df_banknifty_calculated, st.session_state.banknifty_params)
                
        st.write("---")
