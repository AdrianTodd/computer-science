import streamlit as st
import pandas as pd
import requests

### Data Loading Functions ###


@st.cache_data
def load_aeso_data(data_file=None, columns=None):
    """
    Loads historical AESO data from a CSV file.
    """
    try:
        df = pd.read_csv(data_file, usecols=columns)
    except FileNotFoundError:
        st.error(f"Error: '{data_file}' not found.")
        return pd.DataFrame()
    except ValueError as e:
        st.error(f"Error reading CSV: {e}")
        return pd.DataFrame()

    rename_map = {
        "Date_Begin_Local": "datetime_str",
        "ACTUAL_AIL": "demand_mw",
        "ACTUAL_POOL_PRICE": "price_cad",
        "WIND": "wind_mw",
        "SOLAR": "solar_mw",
        "GAS": "gas_mw",
        "COAL": "coal_mw",
        "HYDRO": "hydro_mw",
    }
    cols_to_rename = {k: v for k, v in rename_map.items() if k in df.columns}
    df.rename(columns=cols_to_rename, inplace=True)

    df.drop_duplicates(subset=["datetime_str"], inplace=True)
    df["datetime"] = pd.to_datetime(df["datetime_str"])
    df.set_index("datetime", inplace=True)

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df.asfreq("h")
    df["demand_mw"] = df["demand_mw"].interpolate(method="linear", limit=2)
    df["price_cad"] = df["price_cad"].interpolate(method="linear", limit=2)

    return df


@st.cache_data
def load_hourly_weather_data(start_date, end_date, latitude=51.05, longitude=-114.07):
    """
    Fetches HOURLY historical weather data from Open-Meteo Archive API.
    """
    API_URL = "https://archive-api.open-meteo.com/v1/archive"
    max_archive_date = pd.Timestamp.now().date() - pd.Timedelta(days=2)
    # Ensure start_date/end_date are date objects
    if isinstance(start_date, pd.Timestamp):
        start_date = start_date.date()
    if isinstance(end_date, pd.Timestamp):
        end_date = end_date.date()

    # If the requested start date is already in the future relative to archive, return empty
    if start_date > max_archive_date:
        return pd.DataFrame()

    # Clamp end date
    safe_end_date = min(end_date, max_archive_date)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": safe_end_date.strftime("%Y-%m-%d"),
        "hourly": "temperature_2m",
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

        return hourly_df[["temp_c"]]

    except requests.exceptions.RequestException as e:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_current_weather_data(lat, lon, start_date=None):
    """
    Fetches LIVE/FORECAST weather data from Open-Meteo Forecast API.
    """
    API_URL = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m",
        "past_days": 7,
        "forecast_days": 2,
        "timezone": "America/Denver",
    }
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data["hourly"])
        df["datetime"] = pd.to_datetime(df["time"])
        df.set_index("datetime", inplace=True)
        df.rename(columns={"temperature_2m": "temp_c"}, inplace=True)
        if start_date:
            start_dt = pd.to_datetime(start_date)
            df = df[df.index > start_dt]

        return df[["temp_c"]]
    except Exception as e:
        st.warning(f"Could not fetch live weather: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_realtime_aeso_data(api_key="", start_date=None):
    """
    Fetches the latest grid demand AND pool price from the AESO API.
    Uses two separate endpoints: Actual Forecast Report and Pool Price Report.
    """
    if not api_key:
        return pd.DataFrame()

    end_date = pd.Timestamp.now()

    # If no start date provided, default to today
    if not start_date:
        start_date = end_date

    # Ensure start_date is a Timestamp for calculations
    start_dt = pd.to_datetime(start_date)
    print("Start date for AESO fetch:", start_dt)
    # Using 'D' frequency creates a DatetimeIndex of days
    date_range = pd.date_range(start=start_dt, end=end_date, freq="D")
    print("Date range for AESO fetch:", date_range)
    # If the range is empty (e.g. start=today), make sure we at least fetch today
    if len(date_range) == 0:
        date_range = [end_date]

    s_str = start_dt.strftime("%Y-%m-%d")
    e_str = end_date.strftime("%Y-%m-%d")
    print("Fetching AESO data from", s_str, "to", e_str)

    headers = {
        "API-KEY": api_key,
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    }

    DEMAND_URL = f"https://apimgw.aeso.ca/public/actualforecast-api/v1/load/albertaInternalLoad?startDate={s_str}&endDate={e_str}"
    PRICE_URL = f"https://apimgw.aeso.ca/public/poolprice-api/v1.1/price/poolPrice?startDate={s_str}&endDate={e_str}"

    try:
        # Fetch Demand
        r_demand = requests.get(DEMAND_URL, headers=headers, timeout=10, verify=False)
        r_demand.raise_for_status()
        data_demand = r_demand.json()

        # Fetch Price
        r_price = requests.get(PRICE_URL, headers=headers, timeout=10, verify=False)
        r_price.raise_for_status()
        data_price = r_price.json()

        # Process Demand Response
        demand_list = data_demand.get("return", {}).get("Actual Forecast Report", [])

        df_demand = pd.DataFrame(demand_list)
        if not df_demand.empty:
            df_demand["datetime"] = pd.to_datetime(df_demand["begin_datetime_mpt"])
            df_demand["actual_load"] = pd.to_numeric(
                df_demand["alberta_internal_load"], errors="coerce"
            )
            df_demand["forecast_load"] = pd.to_numeric(
                df_demand["forecast_alberta_internal_load"], errors="coerce"
            )
            df_demand["demand_mw"] = df_demand["actual_load"].fillna(
                df_demand["forecast_load"]
            )

            df_demand.set_index("datetime", inplace=True)
            df_demand = df_demand[["demand_mw"]]

        # Process Price Response
        price_list = data_price.get("return", {}).get("Pool Price Report", [])

        df_price = pd.DataFrame(price_list)
        if not df_price.empty:
            df_price["datetime"] = pd.to_datetime(df_price["begin_datetime_mpt"])
            df_price["actual_price"] = pd.to_numeric(
                df_price["pool_price"], errors="coerce"
            )
            df_price["forecast_price"] = pd.to_numeric(
                df_price["forecast_pool_price"], errors="coerce"
            )
            df_price["price_cad"] = df_price["actual_price"].fillna(
                df_price["forecast_price"]
            )

            df_price.set_index("datetime", inplace=True)
            df_price = df_price[["price_cad"]]

        # Merge using inner join to ensure both for valid rows
        if not df_demand.empty and not df_price.empty:
            df_live = pd.merge(
                df_demand, df_price, left_index=True, right_index=True, how="inner"
            )
            return df_live
        elif not df_demand.empty:
            return df_demand  # Return partial if price fails
        elif not df_price.empty:
            return df_price  # Return partial if demand fails

        return pd.DataFrame()

    except Exception as e:
        st.warning(f"AESO API Error: {e}")
        return pd.DataFrame()


def check_system_alerts(
    current_price, current_demand, current_temp, price_threshold, demand_threshold
):
    """
    Acts as the CONTROLLER in the Environmental Control Pattern.
    """
    alerts = []
    if current_price > price_threshold:
        alerts.append(
            {
                "level": "error",
                "message": f"⚠️ **CRITICAL PRICE ALERT:** Current price \${current_price:.2f} is above \${price_threshold}!",
            }
        )
    if current_demand > demand_threshold:
        alerts.append(
            {
                "level": "warning",
                "message": f"⚡ **HIGH DEMAND WARNING:** Grid load {current_demand:.0f} MW is above {demand_threshold} MW.",
            }
        )
    if current_temp < -20:
        alerts.append(
            {
                "level": "info",
                "message": f"❄️ **EXTREME COLD:** Temperature is {current_temp:.1f}°C. Expect heating load spike.",
            }
        )
    return alerts
