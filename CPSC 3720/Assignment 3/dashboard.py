import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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


if not df_cleaned.empty:
    # Data Preparation
    # Filter for 2 years of data: 2023 - 2025
    start_date = "2023-08-01 0:00"
    end_date = "2025-08-01 0:00"
    df = df_cleaned.loc[start_date:end_date]

    # Data Manipulation
    window_days = 7
    window_size_hours = 24 * window_days
    df["demand_avg"] = df["demand_mw"].rolling(window=window_size_hours).mean()
    df["price_avg"] = df["price_cad"].rolling(window=window_size_hours).mean()

    # Visualization

    sns.set_theme(style="darkgrid")

    # Create a figure with two subplots, sharing the x-axis
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(15, 10), sharex=True)

    # Electricity Demand Plot
    ax1.set_title("Alberta Electricity Demand (AIL) 2023 - 2025", fontsize=16)
    # Plot raw hourly demand (Series 1)
    sns.lineplot(
        data=df,
        x=df.index,
        y="demand_mw",
        label="Hourly Demand",
        color="lightblue",
        alpha=0.8,
        ax=ax1,
    )
    # Plot 7-day running average of hourly demand (Series 2)
    sns.lineplot(
        data=df,
        x=df.index,
        y="demand_avg",
        label=f"{window_days}-Day Avg.",
        color="blue",
        linewidth=2,
        ax=ax1,
    )
    ax1.set_ylabel("Demand (MW)")
    ax1.legend()

    # --- Electricity Pool Price Plot ---
    ax2.set_title("Alberta Electricity Price 2023 - 2025", fontsize=16)

    # Subplot 2:
    # Raw Hourly Price (Series 3)
    sns.lineplot(
        data=df,
        x=df.index,
        y="price_cad",
        label="Hourly Price",
        color="lightsalmon",
        alpha=0.8,
        ax=ax2,
    )
    # Plot 7-day running average of hourly price (Series 4)
    sns.lineplot(
        data=df,
        x=df.index,
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
        "Alberta Electricity Demand and Price Analysis (2023 - 2025)",
        fontsize=20,
        y=1.03,
    )
    plt.tight_layout()

    # Display plots
    st.pyplot(fig)

    # Show Raw Data Table
    if st.checkbox("Show 2023 Raw Data Table"):
        st.subheader("Raw Data (2023)")
        st.dataframe(df)
