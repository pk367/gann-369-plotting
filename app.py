import pandas as pd
import streamlit as st
from tvDatafeed import TvDatafeed, Interval
from lightweight_charts import Chart

# Streamlit App
st.set_page_config(layout="wide", page_title="Stock Chart with Vertical Line")
st.title("Stock Chart with Vertical Line using TvDatafeed")

# Input fields
symbol = st.text_input("Symbol", "sbin")
exchange = st.text_input("Exchange", "nse")
interval_options = {"1 Day": Interval.in_daily, "1 Hour": Interval.in_1_hour, "4 Hour": Interval.in_4_hour, "Weekly": Interval.in_weekly}
interval = st.selectbox("Interval", list(interval_options.keys()))
n_bars = st.slider("Number of bars", 100, 1000, 300)
selected_date = st.date_input("Select Date for Vertical Line")

# Fetch Data Button
if st.button("Fetch Data"):
    with st.spinner("Fetching data..."):
        try:
            tv = TvDatafeed()
            data = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval_options[interval], n_bars=n_bars)
            
            if data is not None and not data.empty:
                data = data.reset_index()
                data['date'] = data['datetime'].dt.strftime('%Y-%m-%d')
                
                st.subheader(f"Data for {symbol} on {exchange}")
                st.dataframe(data.head())
                
                chart = Chart()
                chart.set(data[['date', 'open', 'high', 'low', 'close', 'volume']].rename(columns={'date': 'time'}))
                
                # Add vertical line marker
                vertical_line_str = selected_date.strftime('%Y-%m-%d')
                if vertical_line_str in data['date'].values:
                    chart.add_marker({
                        "time": vertical_line_str,
                        "position": "aboveBar",
                        "color": "#ff0000",
                        "shape": "arrowDown",
                        "text": "Selected Date"
                    })
                else:
                    st.warning("Selected date not found in fetched data.")
                
                chart.show()
            else:
                st.error(f"No data found for {symbol} on {exchange}")
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")
