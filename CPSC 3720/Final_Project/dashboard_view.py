import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def setup_page():
    st.set_page_config(
        page_title="Alberta Power Grid Analytics", page_icon="⚡", layout="wide"
    )
    st.title("⚡ Alberta Power Grid Dashboard")


def render_sidebar():
    """Renders sidebar and returns user inputs as a dictionary"""
    st.sidebar.title("Dashboard Controls")
    inputs = {}
    inputs["window_days"] = st.sidebar.slider("Running Average (Days)", 1, 30, 7)
    return inputs


def render_date_selector(min_date):
    """Renders date input based on data limits"""
    default_start = pd.Timestamp.now().date() - pd.Timedelta(days=14)
    default_end = pd.Timestamp.now().date() + pd.Timedelta(days=2)
    return st.sidebar.date_input(
        "Select Date Range",
        value=(default_start, default_end),
        min_value=min_date,
        format="YYYY-MM-DD",
    )


def render_alert_config():
    """Renders alert configuration inputs"""
    with st.expander("⚙️ Configure Alert Thresholds"):
        price_threshold = st.number_input("Price Threshold ($)", value=200)
        demand_threshold = st.number_input("Demand Threshold (MW)", value=11000)
    return price_threshold, demand_threshold


def display_alerts(alerts):
    if alerts:
        for alert in alerts:
            if alert["level"] == "error":
                st.error(alert["message"])
            elif alert["level"] == "warning":
                st.warning(alert["message"])
            else:
                st.info(alert["message"])


def render_metrics(df_view):
    now = pd.Timestamp.now()
    past_data = df_view[df_view.index <= now]

    if not past_data.empty:
        latest_row = past_data.iloc[-1]
        display_time = latest_row.name.strftime("%Y-%m-%d %H:%M")

        st.caption(f"Live Status as of: **{display_time}**")

        c1, c2, c3 = st.columns(3)

        # Grid Load
        if pd.notnull(latest_row["demand_mw"]):
            c1.metric(
                "Grid Load",
                f"{latest_row['demand_mw']:,.0f} MW",
                delta="Latest Reading",
            )
        else:
            c1.metric("Grid Load", "N/A", delta="Data Delayed")

        # Price
        if pd.notnull(latest_row["price_cad"]):
            c2.metric(
                "Pool Price", f"${latest_row['price_cad']:.2f}", delta="Latest Reading"
            )
        else:
            c2.metric("Pool Price", "N/A", delta="Data Delayed")

        # Temperature
        if pd.notnull(latest_row["temp_c"]):
            c3.metric("Temp", f"{latest_row['temp_c']:.1f} °C", delta="Live Sensor")
        else:
            c3.metric("Temp", "N/A")

    else:
        st.warning("No recent data available to display metrics.")


def render_selection_metrics(selected_row):
    """
    Renders metrics for a user-selected data point from the chart.
    """
    if selected_row is None or selected_row.empty:
        return

    # Extract time and format it
    sel_time = selected_row.name
    time_str = sel_time.strftime("%Y-%m-%d %H:%M")

    with st.container(border=True):
        st.info(f"📍 **Selected Data Point: {time_str}**")
        c1, c2, c3 = st.columns(3)

        val_demand = selected_row.get("demand_mw", float("nan"))
        val_price = selected_row.get("price_cad", float("nan"))
        val_temp = selected_row.get("temp_c", float("nan"))

        c1.metric(
            "Selected Demand",
            f"{val_demand:,.0f} MW" if pd.notnull(val_demand) else "N/A",
        )
        c2.metric(
            "Selected Price", f"${val_price:.2f}" if pd.notnull(val_price) else "N/A"
        )
        c3.metric(
            "Selected Temp", f"{val_temp:.1f} °C" if pd.notnull(val_temp) else "N/A"
        )


def create_plotly_aeso_plot(df_merged, window_days):
    """
    Creates an INTERACTIVE 3-subplot chart using Plotly.
    """
    window_hours = 24 * window_days
    # Calculate rolling averages
    df_merged["demand_avg"] = df_merged["demand_mw"].rolling(window_hours).mean()
    df_merged["price_avg"] = df_merged["price_cad"].rolling(window_hours).mean()
    df_merged["temp_avg"] = df_merged["temp_c"].rolling(window_hours).mean()

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "Electricity Demand (MW)",
            "Pool Price ($/MWh)",
            "Temperature (°C)",
        ),
    )

    # Demand
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["demand_mw"],
            name="Demand",
            mode="lines+markers",  # <--- CRITICAL: Adds clickable dots
            marker=dict(size=3, opacity=0.6),  # Keep them small so they don't clutter
            line=dict(color="lightblue"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["demand_avg"],
            name=f"{window_days}-Day Avg",
            line=dict(color="blue"),
        ),
        row=1,
        col=1,
    )

    # Price
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["price_cad"],
            name="Price",
            mode="lines+markers",  # <--- CRITICAL
            marker=dict(size=3, opacity=0.6),
            line=dict(color="lightgreen"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["price_avg"],
            name=f"{window_days}-Day Avg",
            line=dict(color="green"),
        ),
        row=2,
        col=1,
    )

    # Temperature
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["temp_c"],
            name="Temp",
            mode="lines+markers",  # <--- CRITICAL
            marker=dict(size=3, opacity=0.6),
            line=dict(color="lightcoral"),
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df_merged.index,
            y=df_merged["temp_avg"],
            name=f"{window_days}-Day Avg",
            line=dict(color="red"),
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        height=800,
        title_text="Alberta Energy & Weather Analysis",
        hovermode="x unified",
        clickmode="event",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
