"""
weather_tool.py - Weather via OpenWeatherMap free API
Get API key free at: https://openweathermap.org/api
Add to .env: OPENWEATHER_API_KEY=your_key
"""

import os
import requests
from datetime import datetime

BASE_URL = "https://api.openweathermap.org/data/2.5"


def _get_key():
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        return None, "Error: OPENWEATHER_API_KEY not set in .env file"
    return key, None


def get_weather(city: str) -> str:
    key, err = _get_key()
    if err:
        return err

    try:
        r = requests.get(
            f"{BASE_URL}/weather",
            params={"q": city, "appid": key, "units": "metric"},
            timeout=10,
        )
        if r.status_code == 404:
            return f"Error: City '{city}' not found."
        if r.status_code == 401:
            return "Error: Invalid OpenWeatherMap API key."
        r.raise_for_status()
        d = r.json()

        temp      = d["main"]["temp"]
        feels     = d["main"]["feels_like"]
        humidity  = d["main"]["humidity"]
        desc      = d["weather"][0]["description"].capitalize()
        wind      = d["wind"]["speed"]
        city_name = d["name"]
        country   = d["sys"]["country"]

        return (
            f"Weather in {city_name}, {country}:\n"
            f"Condition  : {desc}\n"
            f"Temperature: {temp}C (feels like {feels}C)\n"
            f"Humidity   : {humidity}%\n"
            f"Wind       : {wind} m/s"
        )

    except requests.exceptions.ConnectionError:
        return "Error: No internet connection."
    except Exception as e:
        return f"Error fetching weather: {e}"


def get_forecast(city: str, days: int = 3) -> str:
    key, err = _get_key()
    if err:
        return err

    try:
        r = requests.get(
            f"{BASE_URL}/forecast",
            params={"q": city, "appid": key, "units": "metric", "cnt": days * 8},
            timeout=10,
        )
        if r.status_code == 404:
            return f"Error: City '{city}' not found."
        r.raise_for_status()
        d = r.json()

        city_name = d["city"]["name"]
        country   = d["city"]["country"]
        lines     = [f"Forecast for {city_name}, {country}:\n"]

        seen_dates = set()
        for item in d["list"]:
            dt   = datetime.fromtimestamp(item["dt"])
            date = dt.strftime("%b %d")
            if date in seen_dates:
                continue
            seen_dates.add(date)
            if len(seen_dates) > days:
                break

            temp = item["main"]["temp"]
            desc = item["weather"][0]["description"].capitalize()
            lines.append(f"{date}: {desc}, {temp}C")

        return "\n".join(lines)

    except Exception as e:
        return f"Error fetching forecast: {e}"