import streamlit as st
import pandas as pd
import numpy as np
import time

# ----------------------------
# App config
# ----------------------------
st.set_page_config(page_title="Disparity Index Backtesting", page_icon="📈", layout="wide")

# ----------------------------
# Main Dashboard UI
# ----------------------------
st.title("Dashboard")
st.write("Disparity Index strategy ke saath Nifty aur BankNifty backtest karein.")

# ----------------------------
# Index Settings Section
# ----------------------------
st.header("Nifty")
with st.expander("⚙️ Nifty Settings"):
    st.info("Nifty-specific settings can go here.")
    nifty_params = {
        'SMA_Period': st.slider("SMA Period", 5, 50, 20),
        'Buy_Threshold': st.slider("Buy Threshold", 1.0, 5.0, 2.5),
        'Sell_Threshold': st.slider("Sell Threshold", -1.0, -5.0, -2.5)
    }

st.header("BankNifty")
with st.expander("⚙️ BankNifty Settings"):
    st.info("BankNifty-specific settings can go here.")
    banknifty_params = {
        'SMA_Period': st.slider("SMA Period", 5, 50, 20),
        'Buy_Threshold': st.slider("Buy Threshold", 1.0, 5.0, 2.5),
        'Sell_Threshold': st.slider("Sell Threshold", -1.0, -5.0, -2.5)
    }

# ----------------------------
# Backtesting Functionality
# ----------------------------
@st.cache_data
def run_backtest(index: str, period: str):
    """Simulates a backtest and returns a dataframe with results."""
    
    st.info(f"Running {period} backtest for {index}...")
    
    # Simulate a time-consuming process
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.01)
        progress_bar.progress(i + 1)
    
    progress_bar.empty()
    st.success(f"Backtest completed for {index}!")
    
    # Simulate backtest results
    if period == "5-year":
        total_return = np.random.uniform(0.5, 2.0)
        cagr = (1 + total_return)**(1/5) - 1
        max_drawdown = np.random.uniform(0.15, 0.40)
        sharpe_ratio = np.random.uniform(0.8, 1.5)
        num_points = 252 * 5
    else: # 1-year
        total_return = np.random.uniform(0.1, 0.5)
        cagr = total_return
        max_drawdown = np.random.uniform(0.05, 0.20)
        sharpe_ratio = np.random.uniform(0.5, 1.2)
        num_points = 252
    
    # Generate mock equity curve data
    dates = pd.date_range(end=pd.Timestamp.today(), periods=num_points, freq='B')
    returns = np.random.normal(cagr / 252, 0.015, num_points)
    cumulative_returns = (1 + returns).cumprod()
    
    results = pd.DataFrame({
        'Date': dates,
        'Equity': cumulative_returns * 100000  # Start with 1 Lakh
    })
    
    return results, total_return, cagr, max_drawdown, sharpe_ratio

# ----------------------------
# Auto Trading & Backtesting UI
# ----------------------------
st.subheader("Auto Trading & Backtesting")

col1, col2 = st.columns(2)
with col1:
    index_choice = st.radio("Select Index", ["Nifty", "BankNifty"])
with col2:
    backtest_period = st.selectbox("Select Backtest Period", ["1-year", "5-year"])

if st.button("Run Backtest", use_container_width=True):
    # This button will trigger the backtest
    st.markdown("---")
    st.subheader(f"📊 {backtest_period.title()} Backtest Results for {index_choice}")
    
    with st.spinner("Calculating..."):
        results_df, total_return, cagr, max_drawdown, sharpe_ratio = run_backtest(index_choice, backtest_period)
        
    st.markdown("### Performance Metrics")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Return", f"{total_return:.2%}")
    metric_cols[1].metric("CAGR", f"{cagr:.2%}")
    metric_cols[2].metric("Max Drawdown", f"{max_drawdown:.2%}")
    metric_cols[3].metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

    st.markdown("### Equity Curve")
    st.line_chart(results_df.set_index('Date'))
