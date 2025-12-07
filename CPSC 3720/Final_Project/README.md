# Alberta Power Grid Analytics Dashboard ⚡
This interactive dashboard integrates historical and real-time data to analyze electricity demand and pricing in Alberta, correlating it with weather conditions in Calgary. It serves as a tool for visualizing energy trends and monitoring grid stability.
## Features
- **Historical Analysis**: Explore long-term trends in grid demand, pool price, and temperature using data from 2020 onwards.
- **Real-Time Monitoring:** View live grid load and pool price updates bridged seamlessly with historical data.
- **Weather Integration:** Correlates energy metrics with historical and forecasted temperature data from Open-Meteo.
- **Interactive Visualizations:** Zoom, pan, and click on data points in the Plotly charts to inspect specific values.
- **Environmental Control System:** Simulates an alert system that triggers warnings for high prices, high demand, or extreme cold.
- **Modular Design:** Built with a Model-View-Controller (MVC) architecture for maintainability and scalability.
## Prerequisites
Ensure you have the following installed:
**Python 3.14**
**pip** (Python package installer)
## Installation
1. **Clone the Repository:**
```
git clone <repository_url>
cd Final_Project
```

3. **Create a Virtual Environment (Recommended):**
**Windows:**
```
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install Dependencies:**
```
pip install streamlit pandas requests plotly matplotlib seaborn
```

## Configuration
1. **Data File:** Ensure the historical AESO CSV file is in the project root directory.
- **Filename:** Hourly_Metered_Volumes_and_Pool_Price_and_AIL_2020-Jul2025.csv
- **Note:** If you have a newer file, update the AESO_DATA_FILE constant in controller.py.
2. **API Key:**
- The dashboard works with historical data out of the box.
- To enable Real-Time features, you need an API Key from the [AESO Developer Portal.](https://developer-apim.aeso.ca/)
- You will then need to put this API key into a .env file and name the key **AESO_API_KEY** = "your API key"
## Usage
1. **Run the Application:** Navigate to the project folder in your terminal (with your venv activated) and run:
```
streamlit run controller.py
```
