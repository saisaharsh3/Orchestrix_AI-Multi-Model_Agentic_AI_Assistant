"""
location_tool.py - Saved user locations (SQLite namespace "user_locations").
"""

from datetime import datetime

from core.storage import get_store

NAMESPACE = "user_locations"


def store_location(user_id: str, latitude: float, longitude: float, name: str = "current") -> str:
    get_store().put(
        NAMESPACE,
        str(user_id),
        {"lat": latitude, "lon": longitude, "name": name, "timestamp": datetime.now().isoformat()},
    )
    return f"Location saved: {name} ({latitude:.4f}, {longitude:.4f})"


def get_user_location(user_id: str) -> dict | None:
    if not user_id:
        return None
    return get_store().get(NAMESPACE, str(user_id))


def set_home_location(user_id: str, latitude: float, longitude: float) -> str:
    return store_location(user_id, latitude, longitude, "home")


def location_to_maps_query(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat},{lon}"
