import streamlit as st
import plotly.graph_objects as go
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import datetime
import time  

# Page Configuration
st.set_page_config(page_title="ClimateWatch", layout="wide")

# --- DATA: REGIONS AND CITIES ---

REGION_MAP = {
    "Luzon": [
        "Manila", "Quezon City", "Caloocan", "Las Piñas", "Makati", "Malabon", 
        "Mandaluyong", "Marikina", "Muntinlupa", "Navotas", "Parañaque", 
        "Pasay", "Pasig", "San Juan", "Taguig", "Valenzuela",
        "Baguio", "Laoag", "Vigan", "Dagupan", "San Fernando", "Tuguegarao", 
        "Santiago", "Angeles", "Olongapo", "Tarlac City", "Batangas City", 
        "Lipa", "Lucena", "Puerto Princesa", "Legazpi", "Naga"
    ],
    "Visayas": ["Iloilo City", "Bacolod", "Cebu City", "Lapu-Lapu", "Mandaue", "Dumaguete", 
                "Tacloban", "Ormoc"],
    "Mindanao": ["Zamboanga City", "Cagayan de Oro", "Davao City", "General Santos", "Butuan", 
                 "Cotabato City", "Surigao City", "Tagum", "Koronadal", "Malaybalay"]
}

# HEAT INDEX CALCULATION
def calculate_heat_index(T, RH):
    if T < 27: return T 
    hi = -8.78469475556 + 1.61139411 * T + 2.33854883889 * RH + \
         -0.14611605 * T * RH - 0.012308094 * T**2 - 0.0164248277778 * RH**2 + \
         0.002211732 * T**2 * RH + 0.00072546 * T * RH**2 - 0.000003582 * T**2 * RH**2
    return round(hi, 1)

# DATAS API
def get_weather_data(city_query):
    API_KEY = "323bc084ef2de6a3749a37d1bb16cfae" 
    curr_url = f"https://api.openweathermap.org/data/2.5/weather?q={city_query},PH&appid={API_KEY}&units=metric"
    fore_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city_query},PH&appid={API_KEY}&units=metric"
    
    try:
        curr_res = requests.get(curr_url, timeout=10)
        fore_res = requests.get(fore_url, timeout=10)
        if curr_res.status_code != 200: return [], [], None

        curr_data = curr_res.json()
        fore_data = fore_res.json()
        
        # OpenWeather 5-Day Forecast (sampled every 24 hours)
        days_label = [pd.to_datetime(fore_data['list'][i]['dt_txt']).strftime('%d %b') for i in range(0, 40, 8)]
        temps = [fore_data['list'][i]['main']['temp'] for i in range(0, 40, 8)]
        humids = [fore_data['list'][i]['main']['humidity'] for i in range(0, 40, 8)]
        
        current = {
            "name": curr_data['name'],
            "temp": curr_data['main']['temp'],
            "humidity": curr_data['main']['humidity'],
            "main_cond": curr_data['weather'][0]['main'],
            "description": curr_data['weather'][0]['description'].title(),
            "lat": curr_data['coord']['lat'],
            "lon": curr_data['coord']['lon']
        }
        return days_label, temps, humids, current
    except: return [], [], [], None

# HISTORICAL DATA (Last 7 Days)
@st.cache_data(ttl=3600)
def get_historical_comparison(lat, lon):
    # End date is yesterday
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    # Start date is 6 days before the end_date to get a total of 7 days
    start_date = end_date - datetime.timedelta(days=6) 
    
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly=temperature_2m,relative_humidity_2m&timezone=Asia%2FSingapore"
    
    try:
        res = requests.get(url, timeout=10).json()
        # Slicing [12::24] picks the noon (12:00 PM) data point for each day
        hist_temps = res['hourly']['temperature_2m'][12::24]
        hist_rh = res['hourly']['relative_humidity_2m'][12::24]
        hist_times = res['hourly']['time'][12::24]
        
        hist_days = [pd.to_datetime(t).strftime('%d %b') for t in hist_times]
        hist_hi = [calculate_heat_index(t, rh) for t, rh in zip(hist_temps, hist_rh)]
        
        return hist_days, hist_temps, hist_hi
    except:
        return [], [], []

@st.cache_data(ttl=600)
def get_ph_map_data():
    API_KEY = "323bc084ef2de6a3749a37d1bb16cfae"
    all_cities = [city for sublist in REGION_MAP.values() for city in sublist]
    
    def fetch_city(c):
        url = f"https://api.openweathermap.org/data/2.5/weather?q={c},PH&appid={API_KEY}&units=metric"
        try:
            res = requests.get(url, timeout=5).json()
            return {"city": c, "lat": res['coord']['lat'], "lon": res['coord']['lon'], "temp": res['main']['temp']}
        except: return None

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(fetch_city, all_cities))
    return pd.DataFrame([r for r in results if r])

# 
@st.fragment(run_every="1s")
def display_live_time():
    now = datetime.datetime.now()
    st.markdown(f" Date: {now.strftime('%A, %d %B %Y')}")
    st.markdown(f" Time: {now.strftime('%I:%M:%S %p')}")

# --- MAIN UI ---
st.title("Philippine Weather Dashboard")

# --- SIDEBAR: REGIONAL SELECTION ---
st.sidebar.header("Geography Filter")
selected_region = st.sidebar.selectbox("", list(REGION_MAP.keys()))
city_options = REGION_MAP[selected_region]
selected_city = st.sidebar.selectbox(f"Select City in {selected_region}", city_options)
manual_search = st.sidebar.text_input(" Manual Search ", placeholder="Type any PH city...")
final_city = manual_search if manual_search else selected_city

# SIDEBAR SOURCES
st.sidebar.divider()
st.sidebar.subheader("WEATHER SOURCES/REFERENCES")
st.sidebar.markdown("""
Learn more about PH weather from official sources:
* [PAGASA Official](https://www.pagasa.dost.gov.ph/)
* [Project NOAH](https://noah.up.edu.ph/)
* [PANaHON (PAGASA)](https://www.panahon.gov.ph/)
* [OpenWeatherMap](https://openweathermap.org/)
* [Windy.com (PH)](https://www.windy.com/)
""")

# --- MAP SECTION ---
df_map = get_ph_map_data()
selected_city_data = df_map[df_map['city'].str.lower() == final_city.lower()]

if not selected_city_data.empty:
    t_lat, t_lon, t_zoom = selected_city_data.iloc[0]['lat'], selected_city_data.iloc[0]['lon'], 12
else:
    t_lat, t_lon, t_zoom = 12.8797, 121.7740, 4.5

if not df_map.empty:
    fig_map = go.Figure(go.Scattermapbox(
        lat=df_map['lat'], lon=df_map['lon'], mode='markers+text',
        marker=go.scattermapbox.Marker(size=12, color=df_map['temp'], colorscale='YlOrRd', showscale=True),
        text=[f"{c}: {t}°C" for c, t in zip(df_map['city'], df_map['temp'])]
    ))
    fig_map.update_layout(
        mapbox_style="carto-positron", mapbox=dict(center=dict(lat=t_lat, lon=t_lon), zoom=t_zoom),
        height=400, margin={"r":0,"t":0,"l":0,"b":0}
    )
    st.plotly_chart(fig_map, use_container_width=True)

# --- WEATHER DISPLAY ---
f_days, f_temps, f_humids, current_data = get_weather_data(final_city) # type: ignore

if current_data:
    st.divider()
    col_graph, col_stats = st.columns([2, 1])
    
    with col_graph:
        st.subheader(f" Weather Forecast Timeline: {current_data['name']}")
        
        # historical comparison 
        h_days, h_temps, h_hi = get_historical_comparison(current_data['lat'], current_data['lon'])
        
        # Forecast Heat Index calculation
        f_hi = [calculate_heat_index(t, h) for t, h in zip(f_temps, f_humids)] # type: ignore
        
        # COMBINE DATA
        all_days = h_days + f_days
        all_temps = h_temps + f_temps
        all_hi = h_hi + f_hi
        
        if all_days:
            fig_comb = go.Figure()
            
            fig_comb.add_trace(go.Scatter(
                x=all_days, y=all_temps, 
                name='Air Temperature (°C)', 
                line=dict(color='#00CC96', width=4),
                mode='lines+markers'
            ))
            
            fig_comb.add_trace(go.Scatter(
                x=all_days, y=all_hi, 
                name='Heat Index (Real Feel)', 
                line=dict(color='#EF553B', width=2, dash='dash'),
                mode='lines+markers'
            ))

            fig_comb.add_vline(x=len(h_days)-0.5, line_width=2, line_dash="dot", line_color="grey")
            fig_comb.add_annotation(x=len(h_days)-0.5, y=max(all_hi), text="FORECAST START", showarrow=False, textangle=-90, xshift=15)

            fig_comb.update_layout(
                template="plotly_white", 
                height=500, 
                hovermode="x unified",
                xaxis_title="Date Timeline (Past 7 days -> Next 5 Days)",
                yaxis_title="Temperature (°C)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_comb, use_container_width=True)
        else:
            st.info("Unified timeline unavailable.")

    with col_stats:
        # LIVE TIME DISPLAY
        display_live_time()
        
        st.subheader("Current Status")
        condition_map = {"Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️", "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️"}
        emoji = condition_map.get(current_data['main_cond'], "🌍")
        st.markdown(f"### {emoji} {current_data['description']}")
        
        heat_idx = calculate_heat_index(current_data['temp'], current_data['humidity'])
        st.metric(label="Temperature", value=f"{current_data['temp']}°C")
        st.metric(label="Heat Index (Real Feel)", value=f"{heat_idx}°C")
        st.metric(label="Humidity", value=f"{current_data['humidity']}%")
        
        diff = f_temps[-1] - f_temps[0]
        if diff < 0:
            st.info(f"Cooler weather expected by end of week ({abs(round(diff, 1))}°C drop).")
        else:
            st.warning(f"Warmer weather expected by end of week ({round(diff, 1)}°C rise).")

        st.divider()
        st.subheader("Health Advisory")
        
        if heat_idx < 27:
            st.success("**Level: Comfortable**")
            st.markdown("""
            - Enjoy outdoor activities. ITS THE TEMPERATURE IS SAFE OUTSIDE
            
            """)
        elif 27 <= heat_idx < 32:
            st.info("**Level: Caution**")
            st.markdown("""
            - Drink water regularly; wear lightweight clothing.
           
            """)
        elif 32 <= heat_idx < 41:
            st.warning("**Level: Extreme Caution**")
            st.markdown("""
            - Stay in the shade; use fans/AC; hydrate with electrolytes.
            
            """)
        elif 41 <= heat_idx < 54:
            st.error("**Level: DANGER**")
            st.markdown("""
            Limit all outdoor activities; wear hats/umbrellas; 
            """)
        else:
            st.error("**Level: EXTREME DANGER**")
            st.markdown("""
             Stay indoors; apply cold compresses if feeling faint
            """)

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
    # Table
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

# FOOTER
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align: center; color: grey;">
        <p style="margin-bottom: 5px;"><strong>Project Members</strong></p>
        <p style="font-size: 0.9em;">
            Asna, Madeo Jose  &nbsp;|&nbsp; Brioso, Andrei &nbsp;|&nbsp; 
            Sorongon, Leonard &nbsp;|&nbsp; Bajado, Ronron &nbsp;|&nbsp;
            Pasuquin, Jullian &nbsp;|&nbsp; Sanchez, Althea &nbsp;|&nbsp;
            Vergara, Hanna Leigh
        </p>
        <p style="font-size: 0.8em;"> 2026 WeatherForecast</p>
    </div>
    """,
    unsafe_allow_html=True
)
