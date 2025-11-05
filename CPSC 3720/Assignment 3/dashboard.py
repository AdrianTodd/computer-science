import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import datetime

# Page configuration
st.set_page_config(page_title="AESO Data Dashboard", page_icon="⚡", layout="wide")


@st.cache_data  # tells Streamlit to keep this data in memory

# Data Loading
def load_data():
    aeso_data = "../aeso_data.csv"
    # Define the specific columns to load
    cols_to_use = ["Date_Begin_Local", "ACTUAL_AIL", "ACTUAL_POOL_PRICE"]

    try:
        df = pd.read_csv(aeso_data, usecols=cols_to_use)
    except FileNotFoundError:
        # Show an error in the app if the file is missing
        st.error(f"Error: '{aeso_data}' not found. Please add it to the folder.")
        return pd.DataFrame()
    except ValueError:
        st.error("Error: Could not find required columns. Check the CSV file.")
        return pd.DataFrame()

    # Rename columns
    df.rename(
        columns={
            "Date_Begin_Local": "datetime_str",
            "ACTUAL_AIL": "demand_mw",
            "ACTUAL_POOL_PRICE": "price_cad",
        },
        inplace=True,
    )

    # Remove duplicate datetime entries to account for daylight savings time changes
    df.drop_duplicates(subset=["datetime_str"], inplace=True)

    # Convert the datetime string to a proper datetime object
    df["datetime"] = pd.to_datetime(df["datetime_str"])
    df.set_index("datetime", inplace=True)
    return df[["demand_mw", "price_cad"]]


# Load the data
df_cleaned = load_data()

# Check if data is loaded before creating controls
if not df_cleaned.empty:

    # Sidebar Controls
    st.sidebar.header("Dashboard Controls")
    window_days = st.sidebar.slider(
        label="Select Running Average Window (Days)",
        min_value=1,
        max_value=30,
        value=7,  # Default value
    )

    # Dynamic date range
    start_date = df_cleaned.index.min().date()
    end_date = df_cleaned.index.max().date()
    df = df_cleaned.loc[start_date:end_date]

    # Date Range Dashboard Control
    date_range = st.sidebar.date_input(
        "Select Date Range",
        # Use 2023-2025 as the default range
        value=(datetime.date(2023, 7, 31), datetime.date(2025, 7, 31)),
        min_value=start_date,
        max_value=end_date,
        format="YYYY-MM-DD",
    )

# Main Dashboard
st.title("⚡ Alberta Electricity (AESO) Data Dashboard")


if not df_cleaned.empty and len(date_range) == 2:

    start_date, end_date = date_range

    # Filter data based on selected date range
    df_filtered = df_cleaned.loc[start_date:end_date].copy()

    # Visualization

    # Data Manipulation

    # Running Average Calculation
    window_size_hours = 24 * window_days
    df_filtered["demand_avg"] = (
        df_filtered["demand_mw"].rolling(window=window_size_hours).mean()
    )
    df_filtered["price_avg"] = (
        df_filtered["price_cad"].rolling(window=window_size_hours).mean()
    )

    sns.set_theme(style="darkgrid")

    # Create a figure with two subplots, sharing the x-axis
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(15, 10), sharex=True)

    # Electricity Demand Plot
    ax1.set_title(
        "Alberta Electricity Demand (AIL)",
        fontsize=16,
    )
    # Plot raw hourly demand (Series 1)
    sns.lineplot(
        data=df_filtered,
        x=df_filtered.index,
        y="demand_mw",
        label="Hourly Demand",
        color="lightblue",
        alpha=0.8,
        ax=ax1,
    )
    # Plot 7-day running average of hourly demand (Series 2)
    sns.lineplot(
        data=df_filtered,
        x=df_filtered.index,
        y="demand_avg",
        label=f"{window_days}-Day Avg.",
        color="blue",
        linewidth=2,
        ax=ax1,
    )
    ax1.set_ylabel("Demand (MW)")
    ax1.legend()

    # --- Electricity Pool Price Plot ---
    ax2.set_title("Alberta Electricity Price", fontsize=16)

    # Subplot 2:
    # Raw Hourly Price (Series 3)
    sns.lineplot(
        data=df_filtered,
        x=df_filtered.index,
        y="price_cad",
        label="Hourly Price",
        color="lightsalmon",
        alpha=0.8,
        ax=ax2,
    )
    # Plot 7-day running average of hourly price (Series 4)
    sns.lineplot(
        data=df_filtered,
        x=df_filtered.index,
        y="price_avg",
        label=f"{window_days}-Day Avg.",
        color="red",
        linewidth=2,
        ax=ax2,
    )
    ax2.set_ylabel("Price ($/MWh)")
    ax2.set_xlabel("Date")
    ax2.legend()

    # Set a y-limit for price to make the trend visible
    ax2.set_ylim(-50, 1050)

    plt.suptitle(
        f"Alberta Electricity Demand and Price Analysis {start_date} - {end_date}",
        fontsize=20,
        y=1.03,
    )
    plt.tight_layout()

    # Display plots
    st.pyplot(fig)

    # Show Raw Data Table
    if st.checkbox(f"Show Raw Data Table ({start_date} to {end_date})"):
        st.subheader("Raw Data")
        st.dataframe(df_filtered)

elif df_cleaned.empty:
    st.error("Data could not be loaded. Please check the CSV file.")
else:
    st.warning("Please select a valid date range in the sidebar.")
