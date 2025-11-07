import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests


### Data Loading Functions ###
@st.cache_data  # tells Streamlit to keep this data in memory
def load_aeso_data(data_file=None, columns=None):
    """
    Loads AESO data from a CSV file.
    """
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


@st.cache_data
def load_daily_weather_data(start_date, end_date, latitude=51.05, longitude=-114.07):
    """
    Fetches daily historical weather data from Open-Meteo API with default latitude and longitude as Calgary, AB.
    """
    API_URL = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": "temperature_2m_mean",  # Daily average temperature
        "timezone": "America/Denver",
    }

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()

        # Process the API response
        weather_df = pd.DataFrame(data["daily"])
        weather_df["datetime"] = pd.to_datetime(weather_df["time"])
        weather_df.set_index("datetime", inplace=True)
        weather_df.rename(columns={"temperature_2m_mean": "temp_avg_c"}, inplace=True)

        return weather_df[["temp_avg_c"]]

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching weather data: {e}")
        return pd.DataFrame()


@st.cache_data
def load_hourly_weather_data(start_date, end_date, latitude=51.05, longitude=-114.07):
    """
    Fetches hourly historical weather data from Open-Meteo API with default latitude and longitude as Calgary, AB.
    """
    API_URL = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "hourly": "temperature_2m",  # Request hourly temperature
        "timezone": "America/Denver",
    }

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        hourly_df = pd.DataFrame(data["hourly"])
        hourly_df["datetime"] = pd.to_datetime(hourly_df["time"])
        hourly_df.set_index("datetime", inplace=True)
        hourly_df.rename(columns={"temperature_2m": "temp_c"}, inplace=True)
        return hourly_df.loc[start_date:end_date, ["temp_c"]]

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching hourly weather data: {e}")
        return pd.DataFrame()


### Plotting Functions ###
def create_aeso_plot(
    df,
    start_date,
    end_date,
    window_days,
    demand_color="lightblue",
    demand_avg_color="blue",
    price_color="lightsalmon",
    price_avg_color="red",
):
    """
    Creates a 3-panel plot for AESO data with demand, price, and temperature.
    """

    sns.set_theme(style="darkgrid")

    window_size_hours = 24 * window_days
    df["demand_avg"] = df["demand_mw"].rolling(window=window_size_hours).mean()
    df["price_avg"] = df["price_cad"].rolling(window=window_size_hours).mean()
    df["temp_avg"] = df["temp_c"].rolling(window=window_size_hours).mean()

    # Create a figure with two subplots, sharing the x-axis
    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, ncols=1, figsize=(15, 14), sharex=True)

    # Electricity Demand Plot
    ax1.set_title(
        "Alberta Electricity Demand (AIL)",
        fontsize=16,
    )
    # Plot raw hourly demand
    sns.lineplot(
        data=df,
        x=df.index,
        y="demand_mw",
        label="Hourly Demand",
        color=f"{demand_color}",
        alpha=0.8,
        ax=ax1,
    )
    # Plot 7-day running average of hourly demand
    sns.lineplot(
        data=df,
        x=df.index,
        y="demand_avg",
        label=f"{window_days}-Day Avg.",
        color=f"{demand_avg_color}",
        linewidth=2,
        ax=ax1,
    )
    ax1.set_ylabel("Demand (MW)")
    ax1.legend()

    # Electricity Pool Price Plot
    ax2.set_title("Alberta Electricity Price", fontsize=16)

    # Subplot 2:
    # Raw Hourly Price
    sns.lineplot(
        data=df,
        x=df.index,
        y="price_cad",
        label="Hourly Price",
        color=f"{price_color}",
        alpha=0.8,
        ax=ax2,
    )
    # Plot 7-day running average of hourly price
    sns.lineplot(
        data=df,
        x=df.index,
        y="price_avg",
        label=f"{window_days}-Day Avg.",
        color=f"{price_avg_color}",
        linewidth=2,
        ax=ax2,
    )
    ax2.set_ylabel("Price ($/MWh)")
    ax2.set_xlabel("Date")
    ax2.legend()

    # Set a y-limit for price to make the trend visible
    ax2.set_ylim(-50, 1050)

    # Temperature Plot
    sns.lineplot(
        data=df,
        x=df.index,
        y="temp_c",
        label="Hourly Temp",
        color="lightcoral",
        alpha=0.8,
        ax=ax3,
    )
    # Plot 7-day running average of hourly temperature
    sns.lineplot(
        data=df,
        x=df.index,
        y="temp_avg",
        label=f"{window_days}-Day Avg.",
        color="red",
        linewidth=2,
        ax=ax3,
    )
    ax3.set_ylabel("Temperature (°C)")
    ax3.set_title("Hourly Temperature (Calgary)", fontsize=16)
    ax3.set_xlabel("Date")
    ax3.legend()

    plt.suptitle(
        f"Alberta Electricity Demand and Price Analysis {start_date} - {end_date}",
        fontsize=20,
        y=1.03,
    )
    plt.tight_layout()
    return fig


def create_demand_temp_plot(df_daily_merged):
    """
    Creates a scatter plot of Daily Average Demand vs. Temperature.
    """
    sns.set_theme(style="darkgrid")
    fig, ax = plt.subplots(figsize=(10, 6))

    sns.scatterplot(
        data=df_daily_merged, x="temp_avg_c", y="demand_mw", alpha=0.6, ax=ax
    )

    # Add a regression line to show the trend
    sns.regplot(
        data=df_daily_merged,
        x="temp_avg_c",
        y="demand_mw",
        scatter=False,  # Don't draw the scatter plot twice
        color="red",
        ax=ax,
    )

    ax.set_title("Daily Average Demand vs. Average Temperature")
    ax.set_xlabel("Average Temperature (°C)")
    ax.set_ylabel("Average Demand (MW)")

    return fig
