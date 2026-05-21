"""
google_maps_tool.py - Maps using OpenStreetMap with Google Maps fallback
- Primary: OpenStreetMap (Nominatim) - FREE
- Fallback: Google Maps - if location not found
"""

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests

# Initialize geocoder
geolocator = Nominatim(user_agent="orchestrix_bot")


def _google_maps_url(search_query: str, origin: str = None, destination: str = None) -> str:
    """Generate Google Maps URL with fallback support."""
    if origin and destination:
        # Directions URL
        return f"https://www.google.com/maps/dir/{origin.replace(' ', '+')}/{destination.replace(' ', '+')}"
    else:
        # Search URL
        return f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"


def search_maps(query: str, location: str = "current") -> str:
    """Search for places using OpenStreetMap, fallback to Google Maps."""
    try:
        location_obj = geolocator.geocode(query)
        
        if location_obj:
            return (
                f"📍 **{query}**\n"
                f"Address: {location_obj.address}\n"
                f"Latitude: {location_obj.latitude:.4f}\n"
                f"Longitude: {location_obj.longitude:.4f}\n\n"
                f"🔗 View on OpenStreetMap: https://www.openstreetmap.org/?lat={location_obj.latitude}&lon={location_obj.longitude}&zoom=15"
            )
        
        # ✅ FALLBACK: Not found in OpenStreetMap, use Google Maps
        google_url = _google_maps_url(query)
        return (
            f"📍 **{query}** (not found in OpenStreetMap)\n\n"
            f"🔗 Search on Google Maps:\n"
            f"{google_url}\n\n"
            f"💡 Tip: Try being more specific (e.g., 'amr movies hyderabad')"
        )
    except Exception as e:
        # Fallback URL as last resort
        google_url = _google_maps_url(query)
        return (
            f"❌ Search error: {str(e)}\n\n"
            f"🔗 Try Google Maps instead:\n"
            f"{google_url}"
        )


def get_directions(origin: str, destination: str, user_location_hint: str = None) -> str:
    """Get directions using OpenStreetMap, fallback to Google Maps."""
    try:
        # ✅ Check if origin is already in "lat,lon" format (coordinates)
        if "," in origin and not any(c.isalpha() for c in origin.split(",")[0]):
            try:
                origin_lat, origin_lon = map(float, origin.split(","))
                origin_loc = type('obj', (object,), {
                    'latitude': origin_lat,
                    'longitude': origin_lon,
                    'address': f"({origin_lat:.4f}, {origin_lon:.4f})"
                })()
            except ValueError:
                origin_loc = geolocator.geocode(origin)
        else:
            origin_loc = geolocator.geocode(origin)
        
        # ✅ If user provided location hint, use it to narrow search
        if user_location_hint and not any(c.isdigit() for c in destination):
            # E.g., "SkyView 10 hyderabad" instead of just "SkyView 10"
            search_destination = f"{destination} {user_location_hint}"
        else:
            search_destination = destination
        
        # ✅ Try to geocode destination with location hint
        dest_loc = geolocator.geocode(search_destination)
        
        # ✅ If not found, try without hint (one more attempt)
        if not dest_loc and user_location_hint:
            dest_loc = geolocator.geocode(destination)
        
        # ✅ If either location not found, fallback to Google Maps
        if not origin_loc or not dest_loc:
            google_url = _google_maps_url(None, origin, destination)
            return (
                f"🛣️ **Directions** from {origin} to {destination}\n\n"
                f"❌ Destination '{destination}' not found in OpenStreetMap\n\n"
                f"🔗 Get directions on Google Maps:\n"
                f"{google_url}\n\n"
                f"💡 Tip: Try being more specific (e.g., 'SkyView 10 hyderabad')"
            )
        
        # Calculate distance
        distance = geodesic(
            (origin_loc.latitude, origin_loc.longitude),
            (dest_loc.latitude, dest_loc.longitude)
        ).km
        
        # ✅ OpenStreetMap directions URL
        osm_directions_url = (
            f"https://www.openstreetmap.org/directions?"
            f"engine=osrm_car"
            f"&route={origin_loc.latitude},{origin_loc.longitude};"
            f"{dest_loc.latitude},{dest_loc.longitude}"
        )
        
        return (
            f"🛣️ **Directions** from {origin} to {destination}\n\n"
            f"📏 Distance: {distance:.1f} km\n"
            f"⏱️ Estimated time: {int(distance / 60)} hours drive\n\n"
            f"🗺️ View on OpenStreetMap:\n"
            f"{osm_directions_url}\n\n"
            f"🔗 Alternative (Google Maps):\n"
            f"{_google_maps_url(None, origin, destination)}"
        )
    except Exception as e:
        google_url = _google_maps_url(None, origin, destination)
        return (
            f"❌ Error: {str(e)}\n\n"
            f"🔗 Get directions on Google Maps instead:\n"
            f"{google_url}"
        )


def find_nearby(place_type: str, location: str = "current") -> str:
    """Find nearby places using Overpass API, fallback to Google Maps."""
    try:
        # Parse location (could be "lat,lon" or place name)
        if "," in location:
            lat, lon = map(float, location.split(","))
        else:
            loc_obj = geolocator.geocode(location)
            if not loc_obj:
                # ✅ FALLBACK: Search on Google Maps
                google_url = _google_maps_url(f"{place_type} near {location}")
                return (
                    f"📍 Location '{location}' not found in OpenStreetMap\n\n"
                    f"🔗 Search on Google Maps instead:\n"
                    f"{google_url}"
                )
            lat, lon = loc_obj.latitude, loc_obj.longitude
        
        # Map place types to Overpass tags
        tag_map = {
            "restaurants": "amenity=restaurant",
            "cafes": "amenity=cafe",
            "hotels": "tourism=hotel",
            "parks": "leisure=park",
            "attractions": "tourism=attraction",
            "museums": "tourism=museum",
            "bars": "amenity=bar",
            "gas stations": "amenity=fuel",
            "banks": "amenity=bank",
        }
        
        tag = tag_map.get(place_type.lower(), f"name~{place_type}")
        
        # Overpass API query (1km radius)
        query = f"""
        [bbox:{lat-0.01},{lon-0.01},{lat+0.01},{lon+0.01}];
        ({tag};);
        out center 20;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            
            if not elements:
                # ✅ FALLBACK: Use Google Maps for this place type
                google_url = _google_maps_url(f"{place_type} near my location")
                return (
                    f"📍 No {place_type} found in OpenStreetMap\n\n"
                    f"🔗 Try searching on Google Maps:\n"
                    f"{google_url}\n\n"
                    f"💡 Try: restaurants, hotels, parks, museums, attractions"
                )
            
            output = f"📍 **Nearby {place_type}** (within 1km):\n\n"
            for i, place in enumerate(elements[:8], 1):
                tags = place.get("tags", {})
                name = tags.get("name", "Unknown")
                addr = tags.get("addr:street", "No address")
                
                # Get center point
                center = place.get("center", {})
                if center:
                    p_lat = center.get("lat")
                    p_lon = center.get("lon")
                    map_link = f"https://www.openstreetmap.org/?lat={p_lat}&lon={p_lon}&zoom=16"
                    output += f"{i}. **{name}**\n   {addr}\n   🔗 [View on map]({map_link})\n\n"
                else:
                    output += f"{i}. **{name}**\n   {addr}\n\n"
            
            return output
        else:
            # ✅ FALLBACK: Server error, use Google Maps
            google_url = _google_maps_url(f"{place_type} nearby")
            return (
                f"❌ OpenStreetMap server error\n\n"
                f"🔗 Search on Google Maps instead:\n"
                f"{google_url}"
            )
    
    except Exception as e:
        # ✅ FALLBACK: Exception, use Google Maps
        google_url = _google_maps_url(f"{place_type} nearby")
        return (
            f"❌ Error: {str(e)}\n\n"
            f"🔗 Search on Google Maps instead:\n"
            f"{google_url}"
        )


def find_stops_on_route(origin: str, destination: str, stop_type: str = "restaurants") -> str:
    """Find eating/interesting stops along route using OpenStreetMap, fallback to Google Maps."""
    try:
        origin_loc = geolocator.geocode(origin)
        dest_loc = geolocator.geocode(destination)
        
        # ✅ FALLBACK: If locations not found
        if not origin_loc or not dest_loc:
            google_url = _google_maps_url(None, origin, destination)
            return (
                f"🛣️ **Stops along {origin} → {destination}**\n\n"
                f"❌ Locations not found in OpenStreetMap\n\n"
                f"🔗 Get directions on Google Maps:\n"
                f"{google_url}\n\n"
                f"💡 Then manually explore stops along the route."
            )
        
        # Calculate midpoint between origin and destination
        mid_lat = (origin_loc.latitude + dest_loc.latitude) / 2
        mid_lon = (origin_loc.longitude + dest_loc.longitude) / 2
        
        # Map stop types
        tag_map = {
            "eating": "amenity=restaurant OR amenity=cafe",
            "restaurants": "amenity=restaurant",
            "cafes": "amenity=cafe",
            "interesting": "tourism=attraction OR tourism=museum OR leisure=park",
            "attractions": "tourism=attraction OR tourism=museum",
            "parks": "leisure=park",
            "gas": "amenity=fuel",
        }
        
        tag = tag_map.get(stop_type.lower(), "amenity=restaurant")
        
        # Overpass query - search 2km radius around midpoint
        query = f"""
        [bbox:{mid_lat-0.02},{mid_lon-0.02},{mid_lat+0.02},{mid_lon+0.02}];
        ({tag};);
        out center 15;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data=query, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            
            if not elements:
                # ✅ FALLBACK: Use Google Maps
                google_url = _google_maps_url(None, origin, destination)
                return (
                    f"🛣️ **Stops along {origin} → {destination}**\n\n"
                    f"❌ No {stop_type} stops found on this route\n\n"
                    f"🔗 View on Google Maps and explore manually:\n"
                    f"{google_url}"
                )
            
            distance = geodesic(
                (origin_loc.latitude, origin_loc.longitude),
                (dest_loc.latitude, dest_loc.longitude)
            ).km
            
            output = f"🛣️ **Stops along {origin} → {destination}**\n"
            output += f"📏 Total distance: {distance:.1f} km\n\n"
            output += f"🍽️ **Suggested {stop_type} stops**:\n\n"
            
            for i, place in enumerate(elements[:10], 1):
                tags = place.get("tags", {})
                name = tags.get("name", "Unknown")
                addr = tags.get("addr:street", "No address")
                
                center = place.get("center", {})
                if center:
                    p_lat = center.get("lat")
                    p_lon = center.get("lon")
                    map_link = f"https://www.openstreetmap.org/?lat={p_lat}&lon={p_lon}&zoom=16"
                    output += f"{i}. **{name}**\n   {addr}\n   🔗 [View]({map_link})\n\n"
                else:
                    output += f"{i}. **{name}**\n   {addr}\n\n"
            
            return output
        else:
            # ✅ FALLBACK: Server error
            google_url = _google_maps_url(None, origin, destination)
            return (
                f"❌ OpenStreetMap server error\n\n"
                f"🔗 Try Google Maps:\n"
                f"{google_url}"
            )
    
    except Exception as e:
        # ✅ FALLBACK: Exception
        google_url = _google_maps_url(None, origin, destination)
        return (
            f"❌ Error: {str(e)}\n\n"
            f"🔗 Try Google Maps:\n"
            f"{google_url}"
        )