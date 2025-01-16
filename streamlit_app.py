import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import asyncio

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Enhanced European Data Sources based on EU initiatives
DATA_SOURCES = {
    "agri_prices": "https://agridata.ec.europa.eu/api/v1/prices",
    "fsdn": "https://agriculture.ec.europa.eu/api/fsdn",  # Farm Sustainability Data Network
    "soil_data": "https://esdac.jrc.ec.europa.eu/api/soil",
    "weather": "http://api.openweathermap.org/data/2.5/weather",
    "eurostat": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/",
    "fast_platform": "https://fastplatform.eu/api/v1/"  # FaST Platform API
}

class EuropeanAgriDataService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=24)

    def _cache_data(self, key, data):
        self.cache[key] = {
            "timestamp": datetime.now(),
            "data": data
        }

    def _is_cache_valid(self, key):
        return (key in self.cache and 
                datetime.now() - self.cache[key]["timestamp"] < self.cache_duration)

    async def get_fsdn_data(self, region):
        """Get Farm Sustainability Data Network information"""
        if self._is_cache_valid(f"fsdn_{region}"):
            return self.cache[f"fsdn_{region}"]["data"]
        
        try:
            response = requests.get(f"{DATA_SOURCES['fsdn']}/region/{region}")
            data = response.json()
            self._cache_data(f"fsdn_{region}", data)
            return data
        except:
            return {"sustainability_metrics": {
                "soil_health": "medium",
                "water_efficiency": "high",
                "biodiversity": "medium"
            }}

    async def get_fast_platform_data(self, region):
        """Get FaST Platform agricultural data"""
        if self._is_cache_valid(f"fast_{region}"):
            return self.cache[f"fast_{region}"]["data"]
        
        try:
            response = requests.get(
                f"{DATA_SOURCES['fast_platform']}/agricultural-data",
                params={"region": region}
            )
            data = response.json()
            self._cache_data(f"fast_{region}", data)
            return data
        except:
            return {
                "soil_nutrients": "moderate",
                "recommended_practices": ["crop_rotation", "minimum_tillage"]
            }

    async def get_market_prices(self):
        """Get current agricultural market prices"""
        if self._is_cache_valid("prices"):
            return self.cache["prices"]["data"]
        
        try:
            response = requests.get(DATA_SOURCES["agri_prices"])
            data = response.json()
            self._cache_data("prices", data)
            return data
        except:
            return {
                "Wheat": {"price": 250, "unit": "€/tonne"},
                "Barley": {"price": 220, "unit": "€/tonne"}
            }

    async def get_weather_data(self, lat, lon):
        """Get weather data"""
        if self._is_cache_valid(f"weather_{lat}_{lon}"):
            return self.cache[f"weather_{lat}_{lon}"]["data"]

        try:
            response = requests.get(
                f"{DATA_SOURCES['weather']}?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
            )
            data = response.json()
            self._cache_data(f"weather_{lat}_{lon}", data)
            return data
        except Exception as e:
            return {"temp": None, "humidity": None, "error": str(e)}

def get_recommendations(region_data, sustainability_data, market_data, weather_data):
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""Based on comprehensive European agricultural data:

    Region: {region_data['name']}
    
    Environmental Conditions:
    - Temperature: {weather_data.get('main', {}).get('temp', 'Unknown')}°C
    - Humidity: {weather_data.get('main', {}).get('humidity', 'Unknown')}%
    - Soil Type: {region_data['soil_type']}
    
    Sustainability Metrics:
    - Soil Health: {sustainability_data.get('soil_health', 'Unknown')}
    - Water Efficiency: {sustainability_data.get('water_efficiency', 'Unknown')}
    - Biodiversity: {sustainability_data.get('biodiversity', 'Unknown')}
    
    Market Conditions:
    {json.dumps(market_data, indent=2)}
    
    Provide 3 crop recommendations optimized for sustainability and profitability:
    """
    
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Failed to get recommendations: {e}")
        return None

def main():
    st.title("European Sustainable Agriculture Advisor")
    
    regions = {
        "Tuscany": {
            "name": "Tuscany, Italy",
            "coordinates": (43.7711, 11.2486),
            "soil_type": "Clay-Limestone"
        },
        "Bavaria": {
            "name": "Bavaria, Germany",
            "coordinates": (48.7904, 11.4979),
            "soil_type": "Loess"
        }
    }
    
    region_name = st.selectbox("Select Region", list(regions.keys()))
    region_data = regions[region_name]
    
    if st.button("Get Sustainable Crop Recommendations"):
        with st.spinner("Analyzing agricultural data..."):
            agri_service = EuropeanAgriDataService()
            sustainability_data = asyncio.run(agri_service.get_fsdn_data(region_name))
            market_data = asyncio.run(agri_service.get_market_prices())
            weather_data = asyncio.run(agri_service.get_weather_data(
                region_data["coordinates"][0], region_data["coordinates"][1]
            ))
            
            recommendations = get_recommendations(
                region_data,
                sustainability_data,
                market_data,
                weather_data
            )
            
            st.write("### Sustainable Crop Recommendations")
            st.write(recommendations)

if __name__ == "__main__":
    main()