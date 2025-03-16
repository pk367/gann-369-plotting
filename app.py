import streamlit as st
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
from lightweight_charts.widgets import StreamlitChart
from datetime import timedelta
import numpy as np
import logging
 
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up page configuration
st.set_page_config(layout="wide", page_title="Swing Projection Chart")
st.title("Swing High/Low Projection Chart")

def fetch_data(tv_datafeed, symbol, exchange, interval, n_bars, fut_contract=None):
    """Fetches historical data for the given symbol and interval."""
    try:
        data = tv_datafeed.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars, fut_contract=fut_contract)
        if data is not None and not data.empty:
            # Convert index to UTC and then to Asia/Kolkata
            data.index = pd.to_datetime(data.index).tz_localize('UTC').tz_convert('Asia/Kolkata')
            data = data.round(2)
        else:
            st.error(f"No data found for {symbol} on {exchange} with interval {interval}")
        return data
    except Exception as e:
        st.error(f"Error fetching data for symbol {symbol}: {e}")
        logger.error(f"Error fetching data for symbol {symbol}: {e}")
        return None

def find_swing_dates(data, pvtLenL=3, pvtLenR=3, shunt=1):
    """Finds all swing high and swing low dates using Pine Script logic."""
    high_series = data['high']
    low_series = data['low']
    dates = data.index
    
    swing_high_dates = []
    swing_high_prices = []
    swing_low_dates = []
    swing_low_prices = []
    
    for i in range(pvtLenL, len(data) - pvtLenR):
        current_high = high_series.iloc[i]
        left_highs = high_series.iloc[i - pvtLenL : i]
        right_highs = high_series.iloc[i + 1 : i + 1 + pvtLenR]
        
        if (current_high > left_highs).all() and (current_high > right_highs).all():
            swing_high_dates.append(dates[i])
            swing_high_prices.append(current_high)
        
        current_low = low_series.iloc[i]
        left_lows = low_series.iloc[i - pvtLenL : i]
        right_lows = low_series.iloc[i + 1 : i + 1 + pvtLenR]
        
        if (current_low < left_lows).all() and (current_low < right_lows).all():
            swing_low_dates.append(dates[i])
            swing_low_prices.append(current_low)
    
    return swing_high_dates, swing_high_prices, swing_low_dates, swing_low_prices

def calculate_projected_dates(dates, prices, type_label):
    """Calculate projected dates for each swing date."""
    if not dates:
        return pd.DataFrame()
    
    # Define the projection periods
    periods = [30, 60, 90, 120, 180, 270, 360]
    
    # Create a DataFrame with the base dates and prices
    df = pd.DataFrame({
        f'{type_label} Date': dates,
        f'{type_label} Price': prices
    })
    
    # Calculate and add projected dates
    for period in periods:
        df[f'{type_label} +{period}d'] = [date + timedelta(days=period) for date in dates]
    
    return df

def generate_vertical_lines(projection_df, type_label, color):
    """Generate vertical line markers for lightweight charts."""
    vertical_lines = []
    
    # Define the projection periods
    periods = [30, 60, 90, 120, 180, 270, 360]
    
    # Generate a different color shade for each period
    colors = {
        30: f"{color}88",   # 30 days - lighter
        60: f"{color}99",
        90: f"{color}AA",
        120: f"{color}BB",
        180: f"{color}CC",
        270: f"{color}DD",
        360: f"{color}EE"    # 360 days - darker
    }
    
    for _, row in projection_df.iterrows():
        for period in periods:
            date_col = f'{type_label} +{period}d'
            if pd.notna(row[date_col]):
                # Format the time correctly for lightweight charts
                time_str = row[date_col].strftime('%Y-%m-%d')
                
                vertical_lines.append({
                    'time': time_str,
                    'color': colors[period],
                    'text': f"{type_label} +{period}d",
                    'position': 'aboveBar' if type_label == 'Swing High' else 'belowBar',
                    'shape': 'arrow' if type_label == 'Swing High' else 'arrowUp',
                    'textColor': colors[period]
                })
    
    return vertical_lines

# Input fields for stock symbol and exchange
col1, col2, col3 = st.columns(3)
with col1:
    symbol = st.text_input("Symbol", "sbin")
with col2:
    exchange = st.text_input("Exchange", "NSE")
with col3:
    interval_options = {
        "1 Day": Interval.in_daily,
        "1 Hour": Interval.in_1_hour,
        "4 Hour": Interval.in_4_hour,
        "Weekly": Interval.in_weekly
    }
    interval = st.selectbox("Interval", list(interval_options.keys()))

# Configuration options
col1, col2, col3, col4 = st.columns(4)
with col1:
    n_bars = st.slider("Number of bars", 100, 5000, 1000)
with col2:
    pvtLenL = st.slider("Pivot Length Left", 1, 10, 3)
with col3:
    pvtLenR = st.slider("Pivot Length Right", 1, 10, 3)
with col4:
    show_projections = st.checkbox("Show Projections", True)

# Button to fetch and display data
if st.button("Generate Chart"):
    with st.spinner("Fetching data and generating chart..."):
        try:
            # Initialize TvDatafeed
            tv = TvDatafeed()
            
            # Fetch data
            data = fetch_data(tv, symbol, exchange, interval_options[interval], n_bars)
            
            if data is not None and not data.empty:
                # Find swing highs and lows
                swing_high_dates, swing_high_prices, swing_low_dates, swing_low_prices = find_swing_dates(data, pvtLenL, pvtLenR)
                
                # Calculate projection dates
                high_projection_df = calculate_projected_dates(swing_high_dates, swing_high_prices, "Swing High")
                low_projection_df = calculate_projected_dates(swing_low_dates, swing_low_prices, "Swing Low")
                
                # Reset index to make date a column
                chart_data = data.reset_index()
                
                # Convert datetime to string format that lightweight charts can handle
                chart_data['datetime'] = chart_data['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Rename columns to match what lightweight charts expects
                chart_data = chart_data.rename(columns={
                    'datetime': 'time',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
                
                # Display summary of the data
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader(f"Found {len(swing_high_dates)} Swing Highs")
                    st.dataframe(high_projection_df.head())
                with col2:
                    st.subheader(f"Found {len(swing_low_dates)} Swing Lows")
                    st.dataframe(low_projection_df.head())
                 
                # Create and display the chart
                st.subheader(f"Price Chart for {symbol} with Swing Projections")
                chart = StreamlitChart(width=1200, height=800)
                
                # Set the data and markers
                chart.set(chart_data)
                 
                # Load the chart
                chart.load()
                
                # Export options
                st.download_button(
                    label="Download Swing High Projections CSV",
                    data=high_projection_df.to_csv(index=False),
                    file_name=f"{symbol}_swing_high_projections.csv",
                    mime="text/csv"
                )
                
                st.download_button(
                    label="Download Swing Low Projections CSV",
                    data=low_projection_df.to_csv(index=False),
                    file_name=f"{symbol}_swing_low_projections.csv",
                    mime="text/csv"
                )
                
            else:
                st.error(f"No data found for {symbol} on {exchange}")
                
        except Exception as e:
            st.error(f"Error generating chart: {str(e)}")
            st.exception(e)
