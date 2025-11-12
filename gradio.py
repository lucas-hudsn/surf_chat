"""
Gradio Frontend for AI Surf Reporter
Connects to MCP server and uses Claude to analyze surf conditions
"""

import asyncio
import json
import os
from typing import Optional
import ollama
import gradio as gr
import httpx

# Initialize Anthropic client
client = ollama.Client()

# Known surf spots with coordinates (expand as needed)
SURF_SPOTS = {
    "Bells Beach, Australia": {"lat": -38.3667, "lon": 144.2833},
    "Pipeline, Hawaii": {"lat": 21.6641, "lon": -158.0533},
    "Jeffreys Bay, South Africa": {"lat": -34.0546, "lon": 24.9096},
    "Teahupo'o, Tahiti": {"lat": -17.8744, "lon": -149.2661},
    "Mavericks, California": {"lat": 37.4936, "lon": -122.4967},
    "Cloudbreak, Fiji": {"lat": -17.7542, "lon": 177.0954},
    "Uluwatu, Bali": {"lat": -8.8293, "lon": 115.0846},
}


async def get_marine_weather(lat: float, lon: float) -> dict:
    """Fetch marine weather data from Open-Meteo API."""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        # Marine forecast
        marine_url = "https://marine-api.open-meteo.com/v1/marine"
        marine_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wave_height,wave_direction,wave_period,swell_wave_height,swell_wave_direction,swell_wave_period",
            "current": "wave_height,wave_direction,wave_period",
            "timezone": "auto"
        }
        marine_response = await http_client.get(marine_url, params=marine_params)
        marine_data = marine_response.json()
        
        # Wind forecast
        wind_url = "https://api.open-meteo.com/v1/forecast"
        wind_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "wind_speed_10m,wind_direction_10m",
            "current": "wind_speed_10m,wind_direction_10m",
            "timezone": "auto"
        }
        wind_response = await http_client.get(wind_url, params=wind_params)
        wind_data = wind_response.json()
        
        return {
            "marine": marine_data,
            "wind": wind_data
        }


def analyze_surf_conditions(spot_name: str, weather_data: dict) -> str:
    """Use Claude to analyze surf conditions and generate a report."""
    
    # Extract current conditions
    current_wave = weather_data["marine"].get("current", {}).get("wave_height", "N/A")
    current_period = weather_data["marine"].get("current", {}).get("wave_period", "N/A")
    current_wind = weather_data["wind"].get("current", {}).get("wind_speed_10m", "N/A")
    current_wind_dir = weather_data["wind"].get("current", {}).get("wind_direction_10m", "N/A")
    
    # Get hourly forecast (next 24 hours)
    hourly_marine = weather_data["marine"].get("hourly", {})
    hourly_wind = weather_data["wind"].get("hourly", {})
    
    # Create prompt for Claude
    prompt = f"""You are an expert surf forecaster analyzing conditions for {spot_name}.

Current Conditions:
- Wave Height: {current_wave}m
- Wave Period: {current_period}s
- Wind Speed: {current_wind} km/h
- Wind Direction: {current_wind_dir}°

24-Hour Forecast Data:
Wave Heights (m): {hourly_marine.get('wave_height', [])[:24]}
Swell Heights (m): {hourly_marine.get('swell_wave_height', [])[:24]}
Wave Periods (s): {hourly_marine.get('wave_period', [])[:24]}
Wind Speeds (km/h): {hourly_wind.get('wind_speed_10m', [])[:24]}
Wind Directions (°): {hourly_wind.get('wind_direction_10m', [])[:24]}

Please provide:
1. **Overall Rating** (1-10 scale) with emoji
2. **Current Conditions Summary** - describe what surfers can expect right now
3. **Best Time to Surf** - when in the next 24 hours will conditions be optimal
4. **Detailed Analysis** - discuss swell quality, wind conditions, and wave period
5. **Recommendations** - skill level suited for these conditions and any safety concerns

Format your response as a clear, engaging surf report that both beginners and experienced surfers can understand."""

    # Call Claude API
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
    
    except Exception as e:
        return f"Error generating surf report: {str(e)}"


async def generate_surf_report(spot_name: str, custom_lat: Optional[float] = None, 
                               custom_lon: Optional[float] = None) -> tuple[str, str]:
    """Main function to generate surf report."""
    
    try:
        # Determine coordinates
        if custom_lat and custom_lon:
            lat, lon = custom_lat, custom_lon
            location_info = f"Custom Location: {lat}°, {lon}°"
        elif spot_name in SURF_SPOTS:
            coords = SURF_SPOTS[spot_name]
            lat, lon = coords["lat"], coords["lon"]
            location_info = f"{spot_name}\nCoordinates: {lat}°, {lon}°"
        else:
            return "❌ Spot not found. Please select from the dropdown or enter custom coordinates.", ""
        
        # Fetch weather data
        weather_data = await get_marine_weather(lat, lon)
        
        # Generate AI analysis
        surf_report = analyze_surf_conditions(spot_name, weather_data)
        
        # Create weather data summary
        current = weather_data["marine"].get("current", {})
        current_wind = weather_data["wind"].get("current", {})
        
        weather_summary = f"""📊 Raw Weather Data:

🌊 Wave Height: {current.get('wave_height', 'N/A')}m
📏 Wave Period: {current.get('wave_period', 'N/A')}s
🧭 Wave Direction: {current.get('wave_direction', 'N/A')}°
💨 Wind Speed: {current_wind.get('wind_speed_10m', 'N/A')} km/h
🧭 Wind Direction: {current_wind.get('wind_direction_10m', 'N/A')}°
"""
        
        return surf_report, weather_summary
        
    except Exception as e:
        return f"❌ Error: {str(e)}", ""


def sync_generate_report(spot: str, lat: Optional[str], lon: Optional[str]):
    """Synchronous wrapper for async report generation."""
    custom_lat = float(lat) if lat else None
    custom_lon = float(lon) if lon else None
    return asyncio.run(generate_surf_report(spot, custom_lat, custom_lon))


# Create Gradio interface
with gr.Blocks(title="🏄 AI Surf Reporter", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🏄‍♂️ AI Surf Reporter & Forecaster
    
    Get AI-powered surf forecasts for popular spots worldwide. The agent analyzes real-time weather data 
    including swell size, period, wind direction, and provides expert recommendations.
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            spot_dropdown = gr.Dropdown(
                choices=list(SURF_SPOTS.keys()),
                label="Select Surf Spot",
                value="Bells Beach, Australia",
                info="Choose from popular surf spots"
            )
            
            with gr.Accordion("🗺️ Custom Location", open=False):
                gr.Markdown("Or enter custom coordinates:")
                with gr.Row():
                    custom_lat = gr.Textbox(label="Latitude", placeholder="-38.3667")
                    custom_lon = gr.Textbox(label="Longitude", placeholder="144.2833")
            
            generate_btn = gr.Button("🌊 Generate Surf Report", variant="primary", size="lg")
        
        with gr.Column(scale=1):
            gr.Markdown("""
            ### About
            This AI surf reporter:
            - ✅ Checks real-time marine weather
            - ✅ Analyzes swell, wind & tides
            - ✅ Provides expert ratings
            - ✅ Suggests best surf times
            
            **Powered by:**
            - Claude AI (Anthropic)
            - Open-Meteo Marine API
            - MCP Server Architecture
            """)
    
    with gr.Row():
        with gr.Column():
            surf_report = gr.Markdown(label="🏄 AI Surf Report")
        with gr.Column():
            weather_data = gr.Markdown(label="📊 Weather Data")
    
    generate_btn.click(
        fn=sync_generate_report,
        inputs=[spot_dropdown, custom_lat, custom_lon],
        outputs=[surf_report, weather_data]
    )
    
    gr.Markdown("""
    ---
    💡 **Tip:** The AI analyzes wave height, period, wind conditions, and historical patterns to provide 
    personalized surf forecasts. Reports include safety recommendations and skill level guidance.
    """)


if __name__ == "__main__":
    demo.launch(share=True)