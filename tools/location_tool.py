"""
location_tool.py - Handle user location and geolocation
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

USER_LOCATIONS = {}
LOCATION_FILE = "data/user_locations.json"


def load_user_locations():
    """Load saved user locations from file."""
    global USER_LOCATIONS
    if os.path.exists(LOCATION_FILE):
        try:
            with open(LOCATION_FILE, "r") as f:
                USER_LOCATIONS = json.load(f)
        except:
            USER_LOCATIONS = {}


def save_user_locations():
    """Save user locations to file."""
    os.makedirs("data", exist_ok=True)
    with open(LOCATION_FILE, "w") as f:
        json.dump(USER_LOCATIONS, f, indent=2)


def store_location(user_id: str, latitude: float, longitude: float, name: str = "current") -> str:
    """Store user's location."""
    USER_LOCATIONS[user_id] = {
        "lat": latitude,
        "lon": longitude,
        "name": name,
        "timestamp": str(__import__('datetime').datetime.now())
    }
    save_user_locations()
    return f" Location saved: {name} ({latitude:.4f}, {longitude:.4f})"


def get_user_location(user_id: str) -> dict | None:
    """Get user's saved location."""
    return USER_LOCATIONS.get(user_id)


def set_home_location(user_id: str, latitude: float, longitude: float) -> str:
    """Set user's home location."""
    return store_location(user_id, latitude, longitude, "home")


def location_to_maps_query(lat: float, lon: float) -> str:
    """Convert coordinates to maps query URL."""
    return f"https://maps.google.com/?q={lat},{lon}"