import streamlit as st
import pandas as pd
import dashboard_model as model
import dashboard_view as view

# Constants
AESO_DATA_FILE = "Hourly_Metered_Volumes_and_Pool_Price_and_AIL_2020-Jul2025.csv"
AESO_API_KEY = ""
# api_key = st.secrets["AESO_API_KEY"]
COLS_TO_USE = ["Date_Begin_Local", "ACTUAL_AIL", "ACTUAL_POOL_PRICE"]
LATITUDE = 51.05
LONGITUDE = -114.07


def main():
    # Setup UI
    view.setup_page()

    # Load Historical Data (Foundation)
    df_aeso_hist = model.load_aeso_data(AESO_DATA_FILE, COLS_TO_USE)

    if df_aeso_hist.empty:
        st.error("Historical Data file could not be loaded.")
        return

    # Get User Inputs
    # Sidebar
    user_inputs = view.render_sidebar()
    window_days = user_inputs["window_days"]

    # Date Range (needs history min date)
    date_range = view.render_date_selector(df_aeso_hist.index.min().date())

    # Main Logic Flow
    if len(date_range) == 2:
        start_date_user, end_date_user = date_range
        last_hist_date = df_aeso_hist.index.max()

        with st.spinner("Syncing data..."):
            # Fetch Weather Data
            df_weather_hist = model.load_hourly_weather_data(
                start_date_user, end_date_user, LATITUDE, LONGITUDE
            )

            df_weather_live = pd.DataFrame()
            if end_date_user >= pd.Timestamp.now().date():
                df_weather_live = model.fetch_current_weather_data(
                    LATITUDE, LONGITUDE, start_date=last_hist_date
                )

            # Fetch Live Power Grid Data
            df_grid_live = pd.DataFrame()
            bridge_start_date = last_hist_date  # + pd.Timedelta(days=1)
            if bridge_start_date <= pd.Timestamp.now():
                df_grid_live = model.fetch_realtime_aeso_data(
                    api_key=AESO_API_KEY, start_date=bridge_start_date
                )

        # Merge Data
        # Combine Weather
        df_weather_combined = pd.concat([df_weather_hist, df_weather_live])
        df_weather_combined = df_weather_combined[
            ~df_weather_combined.index.duplicated(keep="last")
        ]

        # Combine Grid
        if not df_grid_live.empty:
            df_grid_combined = pd.concat([df_aeso_hist, df_grid_live])
            df_grid_combined = df_grid_combined.sort_index()
            df_grid_combined = df_grid_combined[
                ~df_grid_combined.index.duplicated(keep="last")
            ]
        else:
            df_grid_combined = df_aeso_hist

        # Final Merge
        df_merged = pd.merge(
            df_grid_combined,
            df_weather_combined,
            left_index=True,
            right_index=True,
            how="outer",
        )

        # Filter View
        df_view = df_merged.loc[str(start_date_user) : str(end_date_user)].copy()

        if not df_view.empty:
            df_view["demand_mw"] = df_view["demand_mw"].interpolate(
                method="linear", limit=24
            )
            df_view["price_cad"] = df_view["price_cad"].interpolate(
                method="linear", limit=24
            )
            df_view["temp_c"] = df_view["temp_c"].interpolate(method="linear", limit=24)

            # Environmental Control System Status
            st.subheader("System Status")

            # Render Metrics
            view.render_metrics(df_view)

            now = pd.Timestamp.now()
            past_data = df_view[df_view.index <= now]

            if not past_data.empty:
                latest_row = past_data.iloc[-1]

                price_thresh, demand_thresh = view.render_alert_config()
                alerts = model.check_system_alerts(
                    latest_row["price_cad"],
                    latest_row["demand_mw"],
                    latest_row["temp_c"],
                    price_thresh,
                    demand_thresh,
                )
                view.display_alerts(alerts)

            # Visualization
            st.divider()
            fig = view.create_plotly_aeso_plot(df_view, window_days)

            # Ensure the chart has a key to prevent reload loops
            selected_points = st.plotly_chart(
                fig,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key="main_chart",
            )

            # Handle user selection
            if (
                selected_points
                and "selection" in selected_points
                and selected_points["selection"]["points"]
            ):
                point = selected_points["selection"]["points"][0]
                selected_time_str = point.get("x")

                if selected_time_str:
                    try:
                        selected_time = pd.to_datetime(selected_time_str)

                        # 1. Handle Timezone Mismatches
                        if (
                            df_view.index.tz is None
                            and selected_time.tzinfo is not None
                        ):
                            selected_time = selected_time.tz_localize(None)
                        elif (
                            df_view.index.tz is not None
                            and selected_time.tzinfo is None
                        ):
                            selected_time = selected_time.tz_localize(df_view.index.tz)

                        # 2. Find Row (Exact or Nearest)
                        sel_row = None
                        if selected_time in df_view.index:
                            sel_row = df_view.loc[selected_time]
                        else:
                            # Robust fallback: find nearest timestamp
                            idx_locs = df_view.index.get_indexer(
                                [selected_time], method="nearest"
                            )
                            if len(idx_locs) > 0 and idx_locs[0] != -1:
                                sel_row = df_view.iloc[idx_locs[0]]

                        # 3. Handle Duplicates (e.g. Daylight Savings overlaps)
                        if isinstance(sel_row, pd.DataFrame):
                            sel_row = sel_row.iloc[0]

                        if sel_row is not None:
                            view.render_selection_metrics(sel_row)

                    except Exception as e:
                        st.warning(f"Could not retrieve details for selection: {e}")
            else:
                st.info("💡 Click on a data point in the chart above to view details.")


if __name__ == "__main__":
    main()
