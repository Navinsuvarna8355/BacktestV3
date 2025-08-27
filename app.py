import requests
from datetime import datetime, timedelta

def download_bhavcopy(date):
    # NSE bhavcopy download link ka format
    # Example: https://archives.nseindia.com/content/historical/EQUITIES/2025/AUG/cm25AUG2025bhav.csv.zip
    date_str = date.strftime("%d%b%Y").upper()
    month_str = date.strftime("%b").upper()
    year_str = date.strftime("%Y")
    
    url = f"https://archives.nseindia.com/content/historical/EQUITIES/{year_str}/{month_str}/cm{date_str}bhav.csv.zip"
    
    # File download karna
    try:
        response = requests.get(url)
        if response.status_code == 200:
            file_name = f"cm{date_str}bhav.csv.zip"
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"File downloaded successfully: {file_name}")
            return file_name
        else:
            print(f"Error downloading file for {date_str}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Pura 3 saal ka data download karne ke liye
end_date = datetime.now()
start_date = end_date - timedelta(days=3*365) # 3 saal ka data
current_date = start_date

while current_date <= end_date:
    download_bhavcopy(current_date)
    current_date += timedelta(days=1)                    'sell_date': index.strftime('%Y-%m-%d'),
                    'sell_price': row['Close'],
                    'pnl': (row['Close'] - open_trade['buy_price']) * (initial_capital / open_trade['buy_price'])
                })
                st.write(f"🛑 **{reason}:** {index.strftime('%Y-%m-%d')} par trade band @ ₹{row['Close']:.2f}")
                in_trade = False
                open_trade = {}
                continue

        # Buy Signal
        if row['hsp_short'] > row['hsp_long'] and not in_trade and (row['hsp_short'] - row['hsp_long']) >= params['threshold']:
            st.write(f"💼 **Buy Signal:** {index.strftime('%Y-%m-%d')} par trade shuru @ ₹{row['Close']:.2f}")
            open_trade = {'buy_date': index.strftime('%Y-%m-%d'), 'buy_price': row['Close']}
            in_trade = True
        
        # Sell Signal
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
        st.subheader("Trade History")
        st.dataframe(pd.DataFrame(trade_log))
    else:
        st.write("Is strategy ke liye koi trade nahi mila.")

# --- Main Logic ---
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

st.header("🔄 Auto Trading & ⏱️ Backtesting")
run_backtest_button = st.button("Run Backtest", key="run_all")

if run_backtest_button:
    st.write("Generating and backtesting 5 years of historical data. This may take a while...")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)
    
    df_nifty = get_historical_data("^NSEI", start_date, end_date)
    df_banknifty = get_historical_data("^NSEBANK", start_date, end_date)

    if df_nifty is not None and not df_nifty.empty:
        df_nifty_calculated = calculate_indicators(df_nifty, st.session_state.nifty_params)
        run_backtest_logic('Nifty', df_nifty_calculated, st.session_state.nifty_params)
    else:
        st.error("Nifty data download karne mein error hua ya data empty hai.")

    st.write("---")

    if df_banknifty is not None and not df_banknifty.empty:
        df_banknifty_calculated = calculate_indicators(df_banknifty, st.session_state.banknifty_params)
        run_backtest_logic('BankNifty', df_banknifty_calculated, st.session_state.banknifty_params)
    else:
        st.error("BankNifty data download karne mein error hua ya data empty hai.")
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
st.header("🔄 Auto Trading &        results_df, total_return, cagr, max_drawdown, sharpe_ratio = run_backtest(index_choice, backtest_period)
        
    st.markdown("### Performance Metrics")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Return", f"{total_return:.2%}")
    metric_cols[1].metric("CAGR", f"{cagr:.2%}")
    metric_cols[2].metric("Max Drawdown", f"{max_drawdown:.2%}")
    metric_cols[3].metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

    st.markdown("### Equity Curve")
    st.line_chart(results_df.set_index('Date'))        results_df, total_return, cagr, max_drawdown, sharpe_ratio = run_backtest(index_choice, backtest_period)
        
    st.markdown("### Performance Metrics")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Return", f"{total_return:.2%}")
    metric_cols[1].metric("CAGR", f"{cagr:.2%}")
    metric_cols[2].metric("Max Drawdown", f"{max_drawdown:.2%}")
    metric_cols[3].metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

    st.markdown("### Equity Curve")
    st.line_chart(results_df.set_index('Date'))
