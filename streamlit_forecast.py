import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# 1. Page Configuration
st.set_page_config(page_title="WeatherForecast 5-Day", layout="wide")

# --- NEW: HEAT INDEX CALCULATION ---
def calculate_heat_index(T, RH):
    """Calculates the Heat Index (Real Feel) based on PAGASA's formula."""
    if T < 27: return T 
    hi = -8.78469475556 + 1.61139411 * T + 2.33854883889 * RH + \
         -0.14611605 * T * RH - 0.012308094 * T**2 - 0.0164248277778 * RH**2 + \
         0.002211732 * T**2 * RH + 0.00072546 * T * RH**2 - 0.000003582 * T**2 * RH**2
    return round(hi, 1)

# 2. Data Fetching Functions
def get_weather_data(city):
    API_KEY = "323bc084ef2de6a3749a37d1bb16cfae" 
    curr_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    fore_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    
    try:
        curr_res = requests.get(curr_url, timeout=10)
        fore_res = requests.get(fore_url, timeout=10)
        
        if curr_res.status_code != 200 or fore_res.status_code != 200:
            return [], [], None

        curr_data = curr_res.json()
        fore_data = fore_res.json()

        days_label = []
        temps = []
        
        for i in range(0, 40, 8):
            item = fore_data['list'][i]
            date_obj = pd.to_datetime(item['dt_txt'])
            days_label.append(date_obj.strftime('%a (%d %b)')) 
            temps.append(item['main']['temp'])
        
        current = {
            "temp": curr_data['main']['temp'],
            "humidity": curr_data['main']['humidity'],
            "feels_like": curr_data['main']['feels_like'],
            "pressure": curr_data['main']['pressure'],
            "description": curr_data['weather'][0]['description'].title()
        }
        return days_label, temps, current
    except Exception as e:
        st.error(f"Error: {e}")
        return [], [], {}

# --- OPTIMIZED: FAST MAP DATA (Parallel Loading) ---
@st.cache_data(ttl=600)
def get_ph_map_data():
    API_KEY = "323bc084ef2de6a3749a37d1bb16cfae"
    ph_cities = ["Manila", "Quezon City", "Caloocan", "Las Piñas", "Makati", "Malabon", "Mandaluyong", 
    "Marikina", "Muntinlupa", "Navotas", "Parañaque", "Pasay", "Pasig", "San Juan", 
    "Taguig", "Valenzuela", "Baguio", "Laoag", "Vigan", "Dagupan", "San Fernando", 
    "Tuguegarao", "Santiago", "Angeles", "Olongapo", "Tarlac City", "Batangas City", 
    "Lipa", "Lucena", "Puerto Princesa", "Legazpi", "Naga", "Iloilo City", "Bacolod", 
    "Cebu City", "Lapu-Lapu", "Mandaue", "Dumaguete", "Tacloban", "Ormoc", 
    "Zamboanga City", "Cagayan de Oro", "Davao City", "General Santos", "Butuan", 
    "Cotabato City", "Surigao City", "Tagum", "Koronadal", "Malaybalay"]
    
    def fetch_city(c):
        url = f"https://api.openweathermap.org/data/2.5/weather?q={c},PH&appid={API_KEY}&units=metric"
        try:
            res = requests.get(url, timeout=5).json()
            return {"city": c, "lat": res['coord']['lat'], "lon": res['coord']['lon'], "temp": res['main']['temp']}
        except: return None

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_city, ph_cities))
    
    return pd.DataFrame([r for r in results if r])

# 3. Main UI
st.title("Weather Dashboard")

# Map Section
df_map = get_ph_map_data()
if not df_map.empty:
    fig_map = go.Figure(go.Scattermapbox(
        lat=df_map['lat'], lon=df_map['lon'],
        mode='markers+text',
        marker=go.scattermapbox.Marker(size=15, color=df_map['temp'], colorscale='YlOrRd', showscale=True),
        text=[f"{c}: {t}°C" for c, t in zip(df_map['city'], df_map['temp'])],
        textposition="top right",
        textfont=dict(family="Arial Black", size=11, color="white") # Improved visibility
    ))
    fig_map.update_layout(
        mapbox_style="carto-positron", # Darker style for better text visibility
        mapbox=dict(center=dict(lat=12.8797, lon=121.7740), zoom=4.5),
        height=500, margin={"r":0,"t":0,"l":0,"b":0}, template="plotly_white"
    )
    st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# Sidebar
ph_list = ["Manila", "Quezon City", "Caloocan", "Las Piñas", "Makati", "Malabon", "Mandaluyong", 
    "Marikina", "Muntinlupa", "Navotas", "Parañaque", "Pasay", "Pasig", "San Juan", 
    "Taguig", "Valenzuela", "Baguio", "Laoag", "Vigan", "Dagupan", "San Fernando", 
    "Tuguegarao", "Santiago", "Angeles", "Olongapo", "Tarlac City", "Batangas City", 
    "Lipa", "Lucena", "Puerto Princesa", "Legazpi", "Naga", "Iloilo City", "Bacolod", 
    "Cebu City", "Lapu-Lapu", "Mandaue", "Dumaguete", "Tacloban", "Ormoc", 
    "Zamboanga City", "Cagayan de Oro", "Davao City", "General Santos", "Butuan", 
    "Cotabato City", "Surigao City", "Tagum", "Koronadal", "Malaybalay"]


city = st.sidebar.selectbox("Select Location", ph_list)


days, temps, current_data = get_weather_data(city)

if current_data:
    col_graph, col_stats = st.columns([2, 1])
    
    with col_graph:
        st.subheader(f"5-Day Forecast Trend: {city}")
        fig_curr = go.Figure()
        fig_curr.add_trace(go.Scatter(
            x=days, y=temps, 
            mode='lines+markers+text', 
            text=[f"{round(t)}°" for t in temps], 
            textposition="top center",
            line=dict(color='#00CC96', width=4, shape='spline') 
        ))
        fig_curr.update_layout(xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, showticklabels=False),
                               height=350, margin=dict(l=20, r=20, t=40, b=20), template="plotly_white")
        st.plotly_chart(fig_curr, use_container_width=True)

    with col_stats:
        st.subheader("Current Status")
        
        # --- NEW: CALCULATE HEAT INDEX ---
        heat_idx = calculate_heat_index(current_data['temp'], current_data['humidity'])
        
        st.metric(label="Now", value=f"{current_data['temp']}°C", delta=f"{current_data['description']}")
        st.metric(label="Heat Index (Real Feel)", value=f"{heat_idx}°C")
        st.metric(label="Humidity", value=f"{current_data['humidity']}%")
        
        # Long term trend
        diff = temps[-1] - temps[0]
        if diff < 0:
            st.info(f"Cooler weather expected by end of week ({abs(round(diff, 1))}°C drop).")
        else:
            st.warning(f"Warmer weather expected by end of week ({round(diff, 1)}°C rise).")
