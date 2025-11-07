import streamlit as st
import pandas as pd
import datetime
import dashboard_helpers as dh

# Page configuration
st.set_page_config(page_title="AESO Data Dashboard", page_icon="⚡", layout="wide")
st.title("Alberta Electricity System Operator (AESO) Data Dashboard ⚡")

# Specify what data to load
aeso_data_file = "../aeso_data.csv"
cols_to_use = ["Date_Begin_Local", "ACTUAL_AIL", "ACTUAL_POOL_PRICE"]

df_aeso = dh.load_aeso_data(aeso_data_file, cols_to_use)

# Calgary's coordinates
latitude = 51.05
longitude = -114.07

if not df_aeso.empty:
    # Dynamic date range dashboard control
    start_date = df_aeso.index.min().date()
    end_date = df_aeso.index.max().date()
    df_weather = dh.load_daily_weather_data(start_date, end_date, latitude, longitude)
    df_weather_hourly = dh.load_hourly_weather_data(
        start_date, end_date, latitude, longitude
    )
else:
    df_weather = pd.DataFrame()

# Sidebar Controls
st.sidebar.header("Dashboard Controls")
if not df_aeso.empty:

    window_days = st.sidebar.slider(
        label="Select Running Average Window (Days)",
        min_value=1,
        max_value=30,
        value=7,  # Default value
    )

    date_range = st.sidebar.date_input(
        "Select Date Range",
        # Use 2023-2025 as the default range
        value=(datetime.date(2023, 7, 31), datetime.date(2025, 7, 31)),
        min_value=start_date,
        max_value=end_date,
        format="YYYY-MM-DD",
    )

if not df_aeso.empty and len(date_range) == 2:

    start_date, end_date = date_range

    # Filter data based on selected date range
    df_filtered = df_aeso.loc[start_date:end_date].copy()

    # Running Average Calculations
    window_size_hours = 24 * window_days
    df_filtered["demand_avg"] = (
        df_filtered["demand_mw"].rolling(window=window_size_hours).mean()
    )
    df_filtered["price_avg"] = (
        df_filtered["price_cad"].rolling(window=window_size_hours).mean()
    )

    if not df_weather_hourly.empty and not df_filtered.empty:
        df_merged_hourly = pd.merge(
            df_filtered,
            df_weather_hourly,
            left_index=True,
            right_index=True,
            how="inner",  # Use 'inner' to only plot times where both datasets exist
        )

        if df_merged_hourly.empty:
            st.warning("No overlapping hourly data found for this range.")
        else:
            fig = dh.create_aeso_plot(
                df_merged_hourly,
                start_date,
                end_date,
                window_days=window_days,
                demand_color="lightblue",
                demand_avg_color="blue",
                price_color="lightsalmon",
                price_avg_color="red",
            )
            st.pyplot(fig)
    else:
        st.warning("Could not load hourly AESO or Weather data.")

    st.header(f"Daily Correlation ({start_date} to {end_date})")

    if not df_weather.empty:
        # Resample hourly demand to daily average
        df_daily_demand = df_filtered.resample("D").mean()

        # Filter weather data
        df_daily_temp = df_weather.loc[start_date:end_date]

        # Merge the two daily datasets
        df_daily_merged = pd.merge(
            df_daily_demand[["demand_mw"]],
            df_daily_temp[["temp_avg_c"]],
            left_index=True,
            right_index=True,
            how="inner",
        )

        if df_daily_merged.empty:
            st.warning("No combined daily data available for this range.")
        else:
            fig = dh.create_demand_temp_plot(df_daily_merged)
            st.pyplot(fig)

            # Show correlation
            corr = df_daily_merged["temp_avg_c"].corr(df_daily_merged["demand_mw"])
            st.metric(label="Demand-Temperature Correlation", value=f"{corr:.3f}")

    # Show Raw Data Table
    if st.checkbox(f"Show Raw Data Table ({start_date} to {end_date})"):
        st.subheader("Raw Data")
        st.dataframe(df_filtered)

elif df_aeso.empty:
    st.error("Data could not be loaded. Please check the data file.")
else:
    st.warning("Please select a valid date range in the sidebar.")
