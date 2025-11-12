"""
MCP Server for Surf Reporting Agent
Provides tools for checking surf conditions via weather API and web search
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent

# Initialize MCP server
app = Server("surf-reporter")

# Store for conversation context
context_store = {}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for the surf agent."""
    return [
        Tool(
            name="get_weather_forecast",
            description="Get marine weather forecast including swell, wind, and tide data for coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the surf spot"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the surf spot"
                    }
                },
                "required": ["latitude", "longitude"]
            }
        ),
        Tool(
            name="search_surf_spot_info",
            description="Search for information about a surf spot including optimal conditions",
            inputSchema={
                "type": "object",
                "properties": {
                    "spot_name": {
                        "type": "string",
                        "description": "Name of the surf spot"
                    },
                    "location": {
                        "type": "string",
                        "description": "General location/region of the spot"
                    }
                },
                "required": ["spot_name"]
            }
        ),
        Tool(
            name="get_spot_coordinates",
            description="Get GPS coordinates for a surf spot",
            inputSchema={
                "type": "object",
                "properties": {
                    "spot_name": {
                        "type": "string",
                        "description": "Name of the surf spot"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location or region"
                    }
                },
                "required": ["spot_name"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute tool calls for the surf agent."""
    
    if name == "get_weather_forecast":
        return await get_weather_forecast(
            arguments["latitude"],
            arguments["longitude"]
        )
    
    elif name == "search_surf_spot_info":
        return await search_surf_spot_info(
            arguments["spot_name"],
            arguments.get("location", "")
        )
    
    elif name == "get_spot_coordinates":
        return await get_spot_coordinates(
            arguments["spot_name"],
            arguments.get("location", "")
        )
    
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def get_weather_forecast(lat: float, lon: float) -> list[TextContent]:
    """Get marine weather forecast using Open-Meteo Marine API (free)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Open-Meteo Marine API - completely free, no API key needed
            url = "https://marine-api.open-meteo.com/v1/marine"
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction,wave_period,wind_wave_height,swell_wave_height,swell_wave_direction,swell_wave_period",
                "daily": "wave_height_max,wave_direction_dominant,wave_period_max",
                "current": "wave_height,wave_direction,wave_period",
                "timezone": "auto"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            marine_data = response.json()
            
            # Also get wind data from regular Open-Meteo API
            url2 = "https://api.open-meteo.com/v1/forecast"
            params2 = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "current": "wind_speed_10m,wind_direction_10m",
                "timezone": "auto"
            }
            
            response2 = await client.get(url2, params=params2)
            response2.raise_for_status()
            wind_data = response2.json()
            
            # Format the response
            result = {
                "location": {"latitude": lat, "longitude": lon},
                "timestamp": datetime.now().isoformat(),
                "current_conditions": {
                    "wave_height_m": marine_data.get("current", {}).get("wave_height"),
                    "wave_direction": marine_data.get("current", {}).get("wave_direction"),
                    "wave_period_s": marine_data.get("current", {}).get("wave_period"),
                    "wind_speed_kmh": wind_data.get("current", {}).get("wind_speed_10m"),
                    "wind_direction": wind_data.get("current", {}).get("wind_direction_10m")
                },
                "hourly_forecast": {
                    "times": marine_data.get("hourly", {}).get("time", [])[:24],
                    "wave_heights": marine_data.get("hourly", {}).get("wave_height", [])[:24],
                    "swell_heights": marine_data.get("hourly", {}).get("swell_wave_height", [])[:24],
                    "wind_speeds": wind_data.get("hourly", {}).get("wind_speed_10m", [])[:24],
                    "wind_directions": wind_data.get("hourly", {}).get("wind_direction_10m", [])[:24]
                },
                "daily_summary": marine_data.get("daily", {})
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error fetching weather data: {str(e)}"
        )]


async def search_surf_spot_info(spot_name: str, location: str) -> list[TextContent]:
    """Search for surf spot information."""
    query = f"{spot_name} surf spot {location} best conditions optimal swell wind direction"
    
    return [TextContent(
        type="text",
        text=f"Search query prepared: '{query}'\n\nNote: In production, this would use a web search API or scrape surf forecasting sites like Surfline, Magic Seaweed, or local surf reports to find optimal conditions for {spot_name}."
    )]


async def get_spot_coordinates(spot_name: str, location: str) -> list[TextContent]:
    """Get coordinates for a surf spot using geocoding."""
    try:
        # Using Open-Meteo Geocoding API (free)
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": f"{spot_name} {location}",
                "count": 5,
                "language": "en",
                "format": "json"
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                results = []
                for result in data["results"][:3]:
                    results.append({
                        "name": result.get("name"),
                        "latitude": result.get("latitude"),
                        "longitude": result.get("longitude"),
                        "country": result.get("country"),
                        "admin1": result.get("admin1")
                    })
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "query": f"{spot_name} {location}",
                        "results": results
                    }, indent=2)
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"No coordinates found for {spot_name} {location}"
                )]
                
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error getting coordinates: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())