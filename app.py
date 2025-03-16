from tvDatafeed import TvDatafeed, Interval
import pandas as pd
import numpy as np
import logging
import plotly.graph_objects as go
import streamlit as st
from datetime import timedelta

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

def plot_candlestick_with_projections(data, high_projections_df, low_projections_df):
    """Create a candlestick chart with projected dates marked as vertical lines."""
    # Create the candlestick chart
    fig = go.Figure()
    
    # Add candlestick trace
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Candlestick'
    ))
    
    # Define colors for different projection periods
    period_colors = {
        30: 'rgba(255, 0, 0, 0.5)',    # Red
        60: 'rgba(255, 165, 0, 0.5)',  # Orange
        90: 'rgba(255, 255, 0, 0.5)',  # Yellow
        120: 'rgba(0, 255, 0, 0.5)',   # Green
        180: 'rgba(0, 0, 255, 0.5)',   # Blue
        270: 'rgba(75, 0, 130, 0.5)',  # Indigo
        360: 'rgba(148, 0, 211, 0.5)'  # Violet
    }
    
    # Add vertical lines for swing high projections
    if not high_projections_df.empty:
        for period in [30, 60, 90, 120, 180, 270, 360]:
            # Ensure the column exists
            column_name = f'Swing High +{period}d'
            if column_name in high_projections_df.columns:
                for date in high_projections_df[column_name]:
                    if date <= data.index[-1]:  # Only add lines for dates in the data range
                        fig.add_shape(
                            type="line",
                            x0=date,
                            y0=data['low'].min(),
                            x1=date,
                            y1=data['high'].max(),
                            line=dict(
                                color=period_colors[period],
                                width=1,
                                dash="dot",
                            ),
                            name=f'High +{period}d'
                        )
    
    # Add vertical lines for swing low projections
    if not low_projections_df.empty:
        for period in [30, 60, 90, 120, 180, 270, 360]:
            # Ensure the column exists
            column_name = f'Swing Low +{period}d'
            if column_name in low_projections_df.columns:
                for date in low_projections_df[column_name]:
                    if date <= data.index[-1]:  # Only add lines for dates in the data range
                        fig.add_shape(
                            type="line",
                            x0=date,
                            y0=data['low'].min(),
                            x1=date,
                            y1=data['high'].max(),
                            line=dict(
                                color=period_colors[period],
                                width=1,
                                dash="dash",
                            ),
                            name=f'Low +{period}d'
                        )
    
    # Add markers for swing high points
    if not high_projections_df.empty:
        fig.add_trace(go.Scatter(
            x=high_projections_df['Swing High Date'],
            y=high_projections_df['Swing High Price'],
            mode='markers',
            marker=dict(
                symbol='triangle-up',
                size=10,
                color='red',
            ),
            name='Swing Highs'
        ))
    
    # Add markers for swing low points
    if not low_projections_df.empty:
        fig.add_trace(go.Scatter(
            x=low_projections_df['Swing Low Date'],
            y=low_projections_df['Swing Low Price'],
            mode='markers',
            marker=dict(
                symbol='triangle-down',
                size=10,
                color='green',
            ),
            name='Swing Lows'
        ))
    
    # Add a legend for the projection date colors
    for period, color in period_colors.items():
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='lines',
            line=dict(color=color, width=2),
            name=f'+{period} days'
        ))
    
    # Update layout
    fig.update_layout(
        title=f'Candlestick Chart with Projected Dates',
        xaxis_title='Date',
        yaxis_title='Price',
        height=800,
        xaxis_rangeslider_visible=False
    )
    
    return fig

def create_projected_dates_table(high_projections_df, low_projections_df):
    """Create tables for the projected dates."""
    # Display swing high projections
    if not high_projections_df.empty:
        st.subheader("Swing High Projections")
        st.dataframe(high_projections_df)
    
    # Display swing low projections
    if not low_projections_df.empty:
        st.subheader("Swing Low Projections")
        st.dataframe(low_projections_df)

def main():
    st.set_page_config(layout="wide")
    
    st.title("Technical Analysis: Swing Points and Projected Dates")
    
    # Sidebar for inputs
    st.sidebar.header("Parameters")
    
    symbol = st.sidebar.text_input("Symbol", "sbin")
    exchange = st.sidebar.text_input("Exchange", "NSE")
    interval_options = [
        "1 minute", "5 minutes", "15 minutes", "30 minutes", "1 hour", 
        "2 hours", "4 hours", "1 day", "1 week", "1 month"
    ]
    selected_interval = st.sidebar.selectbox("Interval", interval_options, index=7)  # Default to 1 day
    
    # Map selected interval to TvDatafeed Interval
    interval_mapping = {
        "1 minute": Interval.in_1_minute,
        "5 minutes": Interval.in_5_minute,
        "15 minutes": Interval.in_15_minute,
        "30 minutes": Interval.in_30_minute,
        "1 hour": Interval.in_1_hour,
        "2 hours": Interval.in_2_hour,
        "4 hours": Interval.in_4_hour,
        "1 day": Interval.in_daily,
        "1 week": Interval.in_weekly,
        "1 month": Interval.in_monthly
    }
    interval = interval_mapping[selected_interval]
    
    n_bars = st.sidebar.number_input("Number of bars", min_value=100, max_value=10000, value=1000)
    pvtLenL = st.sidebar.number_input("Left pivot length", min_value=1, max_value=10, value=3)
    pvtLenR = st.sidebar.number_input("Right pivot length", min_value=1, max_value=10, value=3)
    
    # Button to fetch data and update chart
    if st.sidebar.button("Analyze"):
        with st.spinner("Fetching data..."):
            # Initialize TV Datafeed
            tv = TvDatafeed()
            
            # Fetch data
            data = fetch_data(tv, symbol, exchange, interval, n_bars)
            
            if data is not None and not data.empty:
                # Find all swing dates and prices
                swing_high_dates, swing_high_prices, swing_low_dates, swing_low_prices = find_swing_dates(data, pvtLenL, pvtLenR)
                
                # Calculate projected dates for swing highs and lows
                high_projection_df = calculate_projected_dates(swing_high_dates, swing_high_prices, "Swing High")
                low_projection_df = calculate_projected_dates(swing_low_dates, swing_low_prices, "Swing Low")
                
                # Create and display the chart
                fig = plot_candlestick_with_projections(data, high_projection_df, low_projection_df)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display tables with projected dates
                create_projected_dates_table(high_projection_df, low_projection_df)
                
                # Option to download the data
                st.subheader("Download Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    if not high_projection_df.empty:
                        csv_high = high_projection_df.to_csv(index=False)
                        st.download_button(
                            label="Download Swing High Projections",
                            data=csv_high,
                            file_name=f"{symbol}_swing_high_projections.csv",
                            mime="text/csv"
                        )
                
                with col2:
                    if not low_projection_df.empty:
                        csv_low = low_projection_df.to_csv(index=False)
                        st.download_button(
                            label="Download Swing Low Projections",
                            data=csv_low,
                            file_name=f"{symbol}_swing_low_projections.csv",
                            mime="text/csv"
                        )
            else:
                st.error("Failed to fetch data. Please check your inputs and try again.")

if __name__ == "__main__":
    main()
