import streamlit as st
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from lightweight_charts.widgets import StreamlitChart

# Set up page configuration
st.set_page_config(layout="wide", page_title="Stock Chart")
st.title("Stock Chart using TvDatafeed and Lightweight Charts")

# Input fields for stock symbol and exchange
col1, col2 = st.columns(2)
with col1:
    symbol = st.text_input("Symbol", "sbin")
with col2:
    exchange = st.text_input("Exchange", "nse")

# Interval selection
interval_options = {
    "1 Day": Interval.in_daily,
    "1 Hour": Interval.in_1_hour,
    "4 Hour": Interval.in_4_hour,
    "Weekly": Interval.in_weekly
}
interval = st.selectbox("Interval", list(interval_options.keys()))

# Number of bars to fetch
n_bars = st.slider("Number of bars", 100, 1000, 300)

# Button to fetch and display data
if st.button("Fetch Data"):
    with st.spinner("Fetching data..."):
        try:
            # Initialize TvDatafeed
            tv = TvDatafeed()

            # Fetch data
            data = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval_options[interval], n_bars=n_bars)

            if data is not None and not data.empty:
                # Reset index to make date a column
                data = data.reset_index()

                # Convert datetime to string format that lightweight charts can handle
                data['datetime'] = data['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Rename columns to match what lightweight charts expects
                data = data.rename(columns={
                    'datetime': 'time',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })

                # Display the data
                st.subheader(f"Data for {symbol} on {exchange}")
                st.dataframe(data.head())

                # Create and display the chart
                st.subheader("Price Chart")
                chart = StreamlitChart(width=900, height=600)
                chart.set(data)
                chart.load()

            else:
                st.error(f"No data found for {symbol} on {exchange}")

        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
