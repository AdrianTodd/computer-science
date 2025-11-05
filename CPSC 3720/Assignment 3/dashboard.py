import streamlit as st
import pandas as pd
import datetime
import dashboard_helpers as dh

# Page configuration
st.set_page_config(page_title="AESO Data Dashboard", page_icon="⚡", layout="wide")
st.title("Alberta Electricity System Operator (AESO) Data Dashboard ⚡")

# Load the data
aeso_data_file = "../aeso_data.csv"
# Define the specific columns to load
cols_to_use = ["Date_Begin_Local", "ACTUAL_AIL", "ACTUAL_POOL_PRICE"]
df = dh.load_data(aeso_data_file, cols_to_use)

# Check if data is loaded before creating controls
if not df.empty:

    # Sidebar Controls
    st.sidebar.header("Dashboard Controls")
    window_days = st.sidebar.slider(
        label="Select Running Average Window (Days)",
        min_value=1,
        max_value=30,
        value=7,  # Default value
    )

    # Dynamic date range dashboard control
    start_date = df.index.min().date()
    end_date = df.index.max().date()
    df = df.loc[start_date:end_date]
    date_range = st.sidebar.date_input(
        "Select Date Range",
        # Use 2023-2025 as the default range
        value=(datetime.date(2023, 7, 31), datetime.date(2025, 7, 31)),
        min_value=start_date,
        max_value=end_date,
        format="YYYY-MM-DD",
    )

if not df.empty and len(date_range) == 2:

    start_date, end_date = date_range

    # Filter data based on selected date range
    df_filtered = df.loc[start_date:end_date].copy()

    # Running Average Calculations
    window_size_hours = 24 * window_days
    df_filtered["demand_avg"] = (
        df_filtered["demand_mw"].rolling(window=window_size_hours).mean()
    )
    df_filtered["price_avg"] = (
        df_filtered["price_cad"].rolling(window=window_size_hours).mean()
    )

    # Create and display plots
    fig = dh.create_aeso_demand_price_plot(
        df_filtered,
        start_date,
        end_date,
        window_days=window_days,
        demand_color="tab:lightblue",
        demand_avg_color="tab:blue",
        price_color="tab:lightsalmon",
        price_avg_color="tab:red",
    )
    st.pyplot(fig)

    # Show Raw Data Table
    if st.checkbox(f"Show Raw Data Table ({start_date} to {end_date})"):
        st.subheader("Raw Data")
        st.dataframe(df_filtered)

elif df.empty:
    st.error("Data could not be loaded. Please check the data file.")
else:
    st.warning("Please select a valid date range in the sidebar.")
