import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# 1. Page Configuration
st.set_page_config(page_title="WeatherForecast 5-Day", layout="wide")

# HEAT INDEX CALCULATION
def calculate_heat_index(T, RH):
    """Calculation of heat index"""
    if T < 27: return T 
    hi = -8.78469475556 + 1.61139411 * T + 2.33854883889 * RH + \
         -0.14611605 * T * RH - 0.012308094 * T**2 - 0.0164248277778 * RH**2 + \
         0.002211732 * T**2 * RH + 0.00072546 * T * RH**2 - 0.000003582 * T**2 * RH**2
    return round(hi, 1)

# DATAS API
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
        
        # ADDED: main condition and icon code
        current = {
            "temp": curr_data['main']['temp'],
            "humidity": curr_data['main']['humidity'],
            "feels_like": curr_data['main']['feels_like'],
            "pressure": curr_data['main']['pressure'],
            "main_cond": curr_data['weather'][0]['main'],
            "description": curr_data['weather'][0]['description'].title(),
            "icon": curr_data['weather'][0]['icon']
        }
        return days_label, temps, current
    except Exception as e:
        st.error(f"Error: {e}")
        return [], [], {}

# MAP DATAA
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

# MAIN UI
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
        textfont=dict(family="Arial Black", size=11, color="white")
    ))
    fig_map.update_layout(
        mapbox_style="carto-positron",
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
        st.subheader(f"5-Day Forecast: Temperature and Heat Index ({city})")
        forecast_heat_indices = [calculate_heat_index(t, current_data['humidity']) for t in temps]
        
        fig_curr = go.Figure()
        fig_curr.add_trace(go.Scatter(
            x=days, y=temps, mode='lines+markers', name='Air Temperature',
            line=dict(color='#00CC96', width=3, shape='spline'),
            hovertemplate='%{y}°C'
        ))
        fig_curr.add_trace(go.Scatter(
            x=days, y=forecast_heat_indices, mode='lines+markers', name='Heat Index (Real Feel)',
            line=dict(color='#EF553B', width=3, dash='dash', shape='spline'),
            hovertemplate='%{y}°C'
        ))

        fig_curr.update_layout(
            xaxis=dict(showgrid=False), 
            yaxis=dict(title="Temperature (°C)", showgrid=True),
            height=400, margin=dict(l=20, r=20, t=40, b=20), 
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_curr, use_container_width=True)

    with col_stats:
        st.subheader("Current Status")
        
        # weather condition emoticonsss
        condition_map = {
            "Clear": "☀️",
            "Clouds": "☁️",
            "Rain": "🌧️",
            "Drizzle": "🌦️",
            "Thunderstorm": "⛈️",
            "Snow": "❄️",
            "Mist": "🌫️",
            "Fog": "🌫️",
            "Haze": "🌫️"
        }
        emoji = condition_map.get(current_data['main_cond'], "🌍")
        
        # Displaying the "Partly Sunny/Cloudy" status elegantly
        st.markdown(f"### {emoji} {current_data['description']}")
        
        heat_idx = calculate_heat_index(current_data['temp'], current_data['humidity'])
        
        st.metric(label="Temperature", value=f"{current_data['temp']}°C")
        st.metric(label="Heat Index (Real Feel)", value=f"{heat_idx}°C")
        st.metric(label="Humidity", value=f"{current_data['humidity']}%")
        
        diff = temps[-1] - temps[0]
        if diff < 0:
            st.info(f"Cooler weather expected by end of week ({abs(round(diff, 1))}°C drop).")
        else:
            st.warning(f"Warmer weather expected by end of week ({round(diff, 1)}°C rise).")
            
       
#  HEAT ADVISORY & PRECAUTIONS
        st.divider()
        st.subheader("Health Advisory")

        if heat_idx < 27:
            st.success("**Comfortable:** No heat-related precautions needed.")
        elif 27 <= heat_idx < 32:
            st.info("**Caution:** Fatigue is possible with prolonged exposure and activity.")
            st.markdown("- Stay hydrated\n- Take breaks in the shade")
        elif 32 <= heat_idx < 41:
            st.warning("**Extreme Caution:** Heat cramps and exhaustion are possible.")
            st.markdown("- Drink plenty of water\n- Limit heavy outdoor activity")
        elif 41 <= heat_idx < 54:
            st.error("**DANGER:** Heat exhaustion likely; heat stroke possible.")
            st.markdown("""
            **Precautions:**
            * Avoid direct sunlight.
            * Wear lightweight, light-colored clothing.
            * Reduce physical exertion to a minimum.
            """)
        else:
            st.error("**EXTREME DANGER:** Heat stroke is imminent.")
            st.markdown("⚠️ **Stay indoors in an air-conditioned room. Seek medical help immediately if feeling dizzy or nauseous.**")

# --- HEAT INDEX REFERENCE CHART SECTION ---
st.divider()

with st.expander("Complete Heat Index Classification & Health Effects"):
    st.markdown("""
    The Heat Index, also known as the **'Apparent Temperature'**, is what the temperature feels like to the human body when relative humidity is combined with the air temperature.
    """)

  
    hi_data = {
        "Classification": ["Caution", "Extreme Caution", "Danger", "Extreme Danger"],
        "Heat Index Range": ["27°C - 32°C", "33°C - 41°C", "42°C - 51°C", "52°C and above"],
        "Potential Health Effects": [
            "Fatigue is possible with prolonged exposure and activity. Continuing activity could lead to heat cramps.",
            "Heat cramps and heat exhaustion are possible. Continuing activity could lead to heat stroke.",
            "Heat exhaustion is likely. Heat stroke is possible with prolonged exposure and activity.",
            "Heat stroke is imminent."
        ]
    }
    df_hi = pd.DataFrame(hi_data)
    # Style the table
    st.table(df_hi)

    # Visual HEAT chart 
    fig_ref = go.Figure(data=[go.Bar(
        x=["Caution", "Extreme Caution", "Danger", "Extreme Danger"],
        y=[32, 41, 51, 60], # Upper bounds for visualization
        marker_color=['#FFFF00', '#FFA500', '#FF4500', '#8B0000'],
        text=["27-32°C", "33-41°C", "42-51°C", "52°C+"],
        textposition='auto',

    )])

    fig_ref.update_layout(
        title="Heat Index Risk Levels",
        xaxis_title="Risk Category",
        yaxis_title="Upper Temperature Limit (°C)",
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white"
    )
    st.plotly_chart(fig_ref, use_container_width=True)   

# FOOTER / end credits?
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: grey;">
        <p style="margin-bottom: 5px;"><strong>Project Members</strong></p>
        <p style="font-size: 0.9em;">
            Asna, Madeo Jose  &nbsp;|&nbsp; Brioso, Andrei &nbsp;|&nbsp; 
            Sorongon, Leonard &nbsp;|&nbsp; Bajado, Ronron &nbsp;|&nbsp;
            Pasuquin, Jullian &nbsp;|&nbsp; Sanchez, Althea &nbsp;|&nbsp;
            Vergara, Hannah Leigh &nbsp;|&nbsp;
        </p>
        <p style="font-size: 0.8em;"> 2026 WeatherForecast</p>
    </div>
    """,
    unsafe_allow_html=True
)
