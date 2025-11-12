from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_tavily import TavilySearch
from langchain.agents import create_agent
from langchain.tools import tool
from geopy.geocoders import Nominatim
import openmeteo_requests
import pandas as pd


@tool
def geocode_address(address: str) -> tuple[float, float]:
    """
    Get the latitude and longitude of an given address.
    args: 
        address: str address/name to geocode
    returns: 
        tuple of (latitude, longitude) or error message
    """
    geolocator = Nominatim(user_agent="my_app")
    location = geolocator.geocode(address)
    if location:
        return [location.latitude,location.longitude]
    else:
        return "Address not found."
    

@tool
def get_swell(coords: tuple) -> dict:
    """
    Get the swell forecast for the given latitude and longitude.
    args: 
        coords: tuple containing (latitude, longitude)
    returns: 
        dict with hourly weather data
    """
    openmeteo = openmeteo_requests.Client()
    # Define the API URL for marine weather
    url = "https://marine-api.open-meteo.com/v1/marine"

    latitude = coords[0]
    longitude = coords[1]

    # Specify the parameters for the request
    params = {
        "latitude": latitude,  # Example: Latitude for a coastal area
        "longitude": longitude, # Example: Longitude for a coastal area
        "hourly": ["wave_height", "wave_direction", "wave_period"], # Requesting specific marine variables
        "timezone": "Australia/Melbourne" # Specify the desired timezone
    }

    # Make the API request
    responses = openmeteo.weather_api(url, params=params)
    # Process the response
    if responses:
        response = responses[0] # Assuming only one location is requested

        # Extract hourly data
        hourly = response.Hourly()
        hourly_data = {
            "time": pd.to_datetime(hourly.Time(), unit="s"),
            "wave_height": hourly.Variables(0).ValuesAsNumpy(),
            "wave_direction": hourly.Variables(1).ValuesAsNumpy(),
            "wave_period": hourly.Variables(2).ValuesAsNumpy()
        }

        return hourly_data
    else:
        print("No data received from the API.")

@tool
def get_swell(coords: tuple) -> dict:
    """
    Get the get_swell forecast for the given latitude and longitude.
    args: 
        coords: tuple containing (latitude, longitude)
    returns: 
        dict with hourly weather data
    """
    openmeteo = openmeteo_requests.Client()
    # Define the API URL for marine weather
    url = "https://marine-api.open-meteo.com/v1/marine"

    latitude = coords[0]
    longitude = coords[1]

    # Specify the parameters for the request
    params = {
        "latitude": latitude,  # Example: Latitude for a coastal area
        "longitude": longitude, # Example: Longitude for a coastal area
        "hourly": ["wave_height", "wave_direction", "wave_period"], # Requesting specific marine variables
        "timezone": "Australia/Melbourne" # Specify the desired timezone
    }

    # Make the API request
    responses = openmeteo.weather_api(url, params=params)
    # Process the response
    if responses:
        response = responses[0] # Assuming only one location is requested

        # Extract hourly data
        hourly = response.Hourly()
        hourly_data = {
            "time": pd.to_datetime(hourly.Time(), unit="s"),
            "wave_height": hourly.Variables(0).ValuesAsNumpy(),
            "wave_direction": hourly.Variables(1).ValuesAsNumpy(),
            "wave_period": hourly.Variables(2).ValuesAsNumpy()
        }

        return hourly_data
    else:
        print("No data received from the API.")

@tool
def get_wind(coords: tuple) -> dict:
    """
    Get the wind forecast for the given latitude and longitude.
    args: 
        coords: tuple containing (latitude, longitude)
    returns: 
        dict with hourly wind data
    """
    openmeteo = openmeteo_requests.Client()

    latitude = coords[0]
    longitude = coords[1]

    # Specify the parameters for the request
    params = {
        "latitude": latitude,  # Example: Latitude for a coastal area
        "longitude": longitude, # Example: Longitude for a coastal area
        "hourly": ["wind_speed", "wind_direction"], # Requesting specific marine variables
        "timezone": "Australia/Melbourne" # Specify the desired timezone
    }

    # Make the API request
    responses = openmeteo.weather_api(params=params)
    # Process the response
    if responses:
        response = responses[0] # Assuming only one location is requested

        # Extract hourly data
        hourly = response.Hourly()
        hourly_data = {
            "time": pd.to_datetime(hourly.Time(), unit="s"),
            "wind_speed": hourly.Variables(0).ValuesAsNumpy(),
            "wind_direction": hourly.Variables(1).ValuesAsNumpy()
        }

        return hourly_data
    else:
        print("No data received from the API.")


agent = create_agent(
    model="ollama:qwen3:4B",
    tools=[geocode_address, get_swell, get_wind],
    system_prompt="You are a helpful assistant that can provide geocoding and surf forecast information based on user queries.",
)
"""
# Run the agent
response = agent.invoke(
    {"messages": [{"role": "user", "content": "Is the surf good in Kilcunda today?"}]}
)
"""
response = agent.invoke(
        {
        "input":
            "Rate the surf in Kilcunda today on a scale of 1 to 10 considering wave height, wave period, and wind conditions."
            }
    )   
        

print(response["messages"][-1].content)
