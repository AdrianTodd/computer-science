import pytest
import pandas as pd
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import dashboard_model as model
import dashboard_view as view


# FIXTURES
@pytest.fixture
def sample_aeso_df():
    """Creates a sample dataframe mimicking the AESO CSV structure."""
    data = {
        "datetime": pd.to_datetime(
            ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"]
        ),
        "demand_mw": [10000, 10500, 10200],
        "price_cad": [50.0, 55.0, 45.0],
        "wind_mw": [100, 150, 120],
    }
    df = pd.DataFrame(data).set_index("datetime")
    return df


@pytest.fixture
def sample_weather_df():
    """Creates a sample dataframe mimicking the Open-Meteo response."""
    data = {
        "datetime": pd.to_datetime(
            ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"]
        ),
        "temp_c": [-10.0, -11.0, -12.0],
    }
    df = pd.DataFrame(data).set_index("datetime")
    return df


# UNIT TESTS: MODEL


def test_check_system_alerts_critical_price():
    """Test that critical price alert is triggered correctly."""
    alerts = model.check_system_alerts(
        current_price=500,
        current_demand=10000,
        current_temp=-10,
        price_threshold=200,
        demand_threshold=11000,
    )
    assert len(alerts) == 1
    assert alerts[0]["level"] == "error"
    assert "CRITICAL PRICE ALERT" in alerts[0]["message"]


def test_check_system_alerts_high_demand():
    """Test that high demand warning is triggered."""
    alerts = model.check_system_alerts(
        current_price=50,
        current_demand=12000,
        current_temp=-10,
        price_threshold=200,
        demand_threshold=11000,
    )
    assert len(alerts) == 1
    assert alerts[0]["level"] == "warning"
    assert "HIGH DEMAND WARNING" in alerts[0]["message"]


def test_check_system_alerts_extreme_cold():
    """Test that extreme cold info is triggered."""
    alerts = model.check_system_alerts(
        current_price=50,
        current_demand=10000,
        current_temp=-25,
        price_threshold=200,
        demand_threshold=11000,
    )
    assert len(alerts) == 1
    assert alerts[0]["level"] == "info"
    assert "EXTREME COLD" in alerts[0]["message"]


def test_check_system_alerts_multiple():
    """Test that multiple alerts can be triggered simultaneously."""
    alerts = model.check_system_alerts(
        current_price=500,
        current_demand=12000,
        current_temp=-30,
        price_threshold=200,
        demand_threshold=11000,
    )
    assert len(alerts) == 3


def test_load_aeso_data_file_not_found():
    """Test that load_aeso_data handles missing file gracefully."""
    # patch st.error so it doesn't try to write to the actual Streamlit UI during tests
    with patch("streamlit.error") as mock_error:
        df = model.load_aeso_data("non_existent_file.csv")
        assert df.empty
        mock_error.assert_called_once()


def test_fetch_current_weather_data_success(mocker):
    """Test fetching weather data with mocked Open-Meteo response."""
    mock_get = mocker.patch("requests.get")

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "hourly": {
            "time": ["2025-01-01T12:00", "2025-01-01T13:00"],
            "temperature_2m": [-5.0, -4.5],
        }
    }
    mock_get.return_value = mock_response

    df = model.fetch_current_weather_data(lat=51.05, lon=-114.07)

    assert not df.empty
    assert "temp_c" in df.columns
    assert df.iloc[0]["temp_c"] == -5.0


# INTEGRATION TESTS: VIEW RENDERING


def test_create_plotly_aeso_plot_structure(sample_aeso_df, sample_weather_df):
    """
    Test that the Plotly figure is created with the correct structure/traces.
    This integrates Model data structures with View logic.
    """
    # Merge the sample dataframes
    df_merged = pd.merge(
        sample_aeso_df, sample_weather_df, left_index=True, right_index=True
    )

    # Run the view function
    fig = view.create_plotly_aeso_plot(df_merged, window_days=1)

    assert fig is not None
    # 6 traces are expected: Demand, Demand_Avg, Price, Price_Avg, Temp, Temp_Avg
    assert len(fig.data) == 6

    # Check trace names
    trace_names = [trace.name for trace in fig.data]
    assert "Demand" in trace_names
    assert "Price" in trace_names
    assert "Temp" in trace_names
