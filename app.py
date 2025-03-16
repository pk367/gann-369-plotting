import streamlit as st
from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import logging
from datetime import timedelta
from streamlit_lightweight_charts import renderLightweightCharts

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def prepare_chart_data(data):
    """Prepare data for the candlestick chart."""
    chart_data = []
    
    for idx, row in data.iterrows():
        timestamp = int(idx.timestamp()) * 1000  # Convert to milliseconds
        chart_data.append({
            "time": timestamp,
            "open": row['open'],
            "high": row['high'],
            "low": row['low'],
            "close": row['close'],
            "volume": row['volume'] if 'volume' in row else 0
        })
    
    return chart_data

def create_vertical_line_markers(dates, colors, labels):
    """Create vertical line markers for the given dates."""
    markers = []
    
    for i, date in enumerate(dates):
        if pd.notna(date):
            timestamp = int(date.timestamp()) * 1000
            markers.append({
                "time": timestamp,
                "position": "aboveBar",
                "color": colors[i % len(colors)],
                "shape": "arrowDown",
                "text": labels[i % len(labels)]
            })
    
    return markers

def main():
    st.set_page_config(layout="wide", page_title="Swing High/Low Analyzer")
    
    st.title("Swing High/Low Analyzer with Projected Dates")
    
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
    
    n_bars = st.slider("Number of bars to fetch", 100, 5000, 1000)
    
    col1, col2 = st.columns(2)
    with col1:
        pvtLenL = st.slider("Left Pivot Length", 1, 10, 3)
    with col2:
        pvtLenR = st.slider("Right Pivot Length", 1, 10, 3)
    
    if st.button("Analyze"):
        with st.spinner("Fetching data..."):
            # Initialize TV Datafeed
            tv = TvDatafeed()
            
            # Fetch data
            data = fetch_data(tv, symbol, exchange, interval_options[interval], n_bars)
            
            if data is not None and not data.empty:
                # Add 'date' column
                data['date'] = data.index
                
                # Find all swing dates and prices
                swing_high_dates, swing_high_prices, swing_low_dates, swing_low_prices = find_swing_dates(data, pvtLenL, pvtLenR)
                
                st.success(f"Analysis completed for {symbol}")
                
                # Calculate projected dates for swing highs and lows
                high_projection_df = calculate_projected_dates(swing_high_dates, swing_high_prices, "Swing High")
                low_projection_df = calculate_projected_dates(swing_low_dates, swing_low_prices, "Swing Low")
                
                # Prepare data for the chart
                chart_data = prepare_chart_data(data)
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["Chart", "Swing High Projections", "Swing Low Projections"])
                
                with tab1:
                    st.subheader(f"Candlestick Chart for {symbol} with Projected Dates")
                    
                    # Prepare chart specification
                    chart_options = {
                        "height": 600,
                        "layout": {
                            "textColor": "black",
                            "background": {
                                "type": "solid",
                                "color": "white"
                            },
                        },
                        "grid": {
                            "vertLines": {
                                "visible": False
                            },
                            "horzLines": {
                                "visible": False
                            }
                        },
                        "timeScale": {
                            "timeVisible": True,
                            "secondsVisible": False
                        },
                        "crosshair": {
                            "mode": 1
                        }
                    }
                    
                    # Create candlestick series
                    series = [{
                        "type": 'Candlestick',
                        "data": chart_data,
                        "options": {
                            "upColor": "#26a69a",
                            "downColor": "#ef5350",
                            "borderVisible": False,
                            "wickUpColor": "#26a69a",
                            "wickDownColor": "#ef5350"
                        }
                    }]
                    
                    # Create markers for projected dates
                    all_markers = []
                    
                    # Colors for different projection periods
                    colors = ["#1E88E5", "#43A047", "#FB8C00", "#E53935", "#8E24AA", "#546E7A", "#D81B60"]
                    periods = [30, 60, 90, 120, 180, 270, 360]
                    
                    # Add markers for swing high projection dates
                    for i, row in high_projection_df.iterrows():
                        for j, period in enumerate(periods):
                            proj_date = row[f'Swing High +{period}d']
                            if pd.notna(proj_date):
                                timestamp = int(proj_date.timestamp()) * 1000
                                all_markers.append({
                                    "time": timestamp,
                                    "position": "aboveBar",
                                    "color": colors[j],
                                    "shape": "arrowDown",
                                    "text": f"H+{period}"
                                })
                    
                    # Add markers for swing low projection dates
                    for i, row in low_projection_df.iterrows():
                        for j, period in enumerate(periods):
                            proj_date = row[f'Swing Low +{period}d']
                            if pd.notna(proj_date):
                                timestamp = int(proj_date.timestamp()) * 1000
                                all_markers.append({
                                    "time": timestamp,
                                    "position": "belowBar",
                                    "color": colors[j],
                                    "shape": "arrowUp",
                                    "text": f"L+{period}"
                                })
                    
                    # Add markers for original swing points
                    for date, price in zip(swing_high_dates, swing_high_prices):
                        if pd.notna(date):
                            timestamp = int(date.timestamp()) * 1000
                            all_markers.append({
                                "time": timestamp,
                                "position": "aboveBar",
                                "color": "#000000",
                                "shape": "circle",
                                "text": "H"
                            })
                    
                    for date, price in zip(swing_low_dates, swing_low_prices):
                        if pd.notna(date):
                            timestamp = int(date.timestamp()) * 1000
                            all_markers.append({
                                "time": timestamp,
                                "position": "belowBar",
                                "color": "#000000",
                                "shape": "circle",
                                "text": "L"
                            })
                    
                    # Add markers to the main series
                    series[0]["markers"] = all_markers
                    
                    # Render the chart
                    renderLightweightCharts(series=series, options=chart_options)
                    
                    # Add a legend for the markers
                    legend_col1, legend_col2, legend_col3, legend_col4 = st.columns(4)
                    with legend_col1:
                        st.markdown("**Marker Legend:**")
                        st.markdown("**H** - Swing High")
                        st.markdown("**L** - Swing Low")
                    with legend_col2:
                        st.markdown("**Color Legend:**")
                        for i, period in enumerate(periods):
                            st.markdown(f"<span style='color:{colors[i]}'>●</span> +{period} days", unsafe_allow_html=True)
                
                with tab2:
                    st.subheader("Swing High Projections")
                    st.dataframe(high_projection_df)
                    
                    if not high_projection_df.empty:
                        csv = high_projection_df.to_csv(index=False)
                        st.download_button(
                            label="Download Swing High Projections",
                            data=csv,
                            file_name=f"{symbol}_swing_high_projections.csv",
                            mime="text/csv",
                        )
                
                with tab3:
                    st.subheader("Swing Low Projections")
                    st.dataframe(low_projection_df)
                    
                    if not low_projection_df.empty:
                        csv = low_projection_df.to_csv(index=False)
                        st.download_button(
                            label="Download Swing Low Projections",
                            data=csv,
                            file_name=f"{symbol}_swing_low_projections.csv",
                            mime="text/csv",
                        )

if __name__ == "__main__":
    main()
