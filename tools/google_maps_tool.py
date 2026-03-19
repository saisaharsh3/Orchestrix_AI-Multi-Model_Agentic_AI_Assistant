"""
google_maps_tool.py - Google Maps integration
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    GOOGLE_MAPS_API_KEY = "demo"


def search_maps(query: str, location: str = "current") -> str:
    """Search for places on Google Maps."""
    if GOOGLE_MAPS_API_KEY == "demo":
        return f"🗺️ Search results for '{query}' near {location}:\n(Demo - requires GOOGLE_MAPS_API_KEY in .env)"
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY,
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if not data.get("results"):
            return f" No places found for '{query}'."
        
        output = f"🗺️ Places for '{query}':\n\n"
        for i, place in enumerate(data["results"][:5], 1):
            name = place.get("name", "Unknown")
            addr = place.get("formatted_address", "No address")
            rating = place.get("rating", "N/A")
            output += f"{i}. **{name}**\n   {addr}\n   Rating: {rating}⭐\n\n"
        return output
    except Exception as e:
        return f"❌ Maps search error: {e}"


def get_directions(origin: str, destination: str) -> str:
    """Get directions between two locations."""
    if GOOGLE_MAPS_API_KEY == "demo":
        return f"🛣️ Directions from {origin} to {destination}:\n(Demo - requires GOOGLE_MAPS_API_KEY)"
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "key": GOOGLE_MAPS_API_KEY,
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if data.get("status") != "OK":
            return f" No route found from {origin} to {destination}."
        
        route = data["routes"][0]
        leg = route["legs"][0]
        distance = leg.get("distance", {}).get("text", "Unknown")
        duration = leg.get("duration", {}).get("text", "Unknown")
        
        output = f"🛣️ **Directions** from {origin} to {destination}:\n\n"
        output += f"📏 Distance: {distance}\n"
        output += f"⏱️ Duration: {duration}\n\n"
        output += "Steps:\n"
        for i, step in enumerate(leg.get("steps", [])[:5], 1):
            instruction = step.get("html_instructions", "").replace("<div style='font-size:0.9em'>", "").replace("</div>", "")
            output += f"{i}. {instruction}\n"
        
        return output
    except Exception as e:
        return f"❌ Directions error: {e}"


def find_nearby(place_type: str, location: str = "current") -> str:
    """Find nearby places of a certain type."""
    if GOOGLE_MAPS_API_KEY == "demo":
        return f"🗺️ Nearby {place_type} near {location}:\n(Demo - requires GOOGLE_MAPS_API_KEY)"
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": place_type,
            "location": location,
            "key": GOOGLE_MAPS_API_KEY,
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if not data.get("results"):
            return f" No {place_type} nearby."
        
        output = f"📍 Nearby **{place_type}**:\n\n"
        for i, place in enumerate(data["results"][:5], 1):
            name = place.get("name", "Unknown")
            addr = place.get("formatted_address", "No address")
            output += f"{i}. {name}\n   {addr}\n\n"
        return output
    except Exception as e:
        return f"❌ Nearby search error: {e}"