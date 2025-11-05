import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


# Data Loading
@st.cache_data  # tells Streamlit to keep this data in memory
def load_data(data_file=None, columns=None):
    try:
        df = pd.read_csv(data_file, usecols=columns)
    except FileNotFoundError:
        # Show an error in the app if the file is missing
        st.error(f"Error: '{data_file}' not found. Please add it to the folder.")
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


def create_aeso_demand_price_plot(
    df,
    start_date,
    end_date,
    window_days,
    demand_color="tab:lightblue",
    demand_avg_color="tab:blue",
    price_color="tab:lightsalmon",
    price_avg_color="tab:red",
):
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
    ax2.set_title("Alberta Electricity Price", fontsize=16)

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
        f"Alberta Electricity Demand and Price Analysis {start_date} - {end_date}",
        fontsize=20,
        y=1.03,
    )
    plt.tight_layout()
    return fig
