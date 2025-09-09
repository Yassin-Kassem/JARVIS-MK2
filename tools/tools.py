import logging 
import requests
import aiohttp
import asyncio
import pythoncom
from livekit.agents import function_tool, RunContext
from langchain_community.tools import DuckDuckGoSearchRun 
from ctypes import cast, POINTER
from comtypes import CoInitialize, CoUninitialize, CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from googlesearch import search as google_search
from bs4 import BeautifulSoup


@function_tool()
async def fetch_weather(city: str) -> dict:
    """
    Fetch current weather for a given city using Open-Meteo API.

    Args:
        city (str): Name of the city

    Returns:
        dict: Weather information including temperature, wind, and conditions
    """
    # Step 1: Get latitude & longitude for the city using Open-Meteo geocoding
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(geo_url) as geo_resp:
            geo_data = await geo_resp.json()
            if "results" not in geo_data or not geo_data["results"]:
                return {"error": f"City '{city}' not found."}
            loc = geo_data["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]

        # Step 2: Fetch current weather for this location
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true"
        )
        async with session.get(weather_url) as weather_resp:
            weather_data = await weather_resp.json()
            if "current_weather" not in weather_data:
                return {"error": "Weather data not available."}

            cw = weather_data["current_weather"]
            return {
                "city": city,
                "temperature": cw["temperature"],  # °C
                "windspeed": cw["windspeed"],     # km/h
                "winddirection": cw["winddirection"], # degrees
                "weathercode": cw["weathercode"], # numerical weather code
            }
            
@function_tool()
async def search_web(context: RunContext, query: str) -> str:
    """
    Search the web using Google Search.
    Returns a short string summary of results.
    """
    try:
        # Simple Google search without problematic parameters
        search_results = await asyncio.to_thread(
            lambda: list(google_search(query))
        )
        
        # Take first 5 results
        search_results = search_results[:5]
        
        if not search_results:
            return f"No results found for '{query}'"
        
        # Format results
        formatted_results = []
        for i, url in enumerate(search_results, 1):
            formatted_results.append(f"{i}. {url}")
        
        result = f"Google search results for '{query}':\n" + "\n".join(formatted_results)
        logging.info(f"Google search completed for '{query}'")
        return result
        
    except Exception as e:
        logging.error(f"Error searching Google for '{query}': {e}")
        return f"An error occurred while searching Google for '{query}'."
