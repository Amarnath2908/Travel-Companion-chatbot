import os
import time
import requests
import wikipedia
from langdetect import detect
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# --- API keys and constants ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
CACHE_TTL = 3600  # seconds

# --- Create Supabase client ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

_cache = {}  # simple in-memory cache {city_lower: (timestamp, reply_str)}

# --- Language detection ---
def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "en"

# --- Helper API functions ---
def _get_weather(city_name):
    """Return weather JSON or None."""
    if not OPENWEATHER_API_KEY:
        return None
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_name, "appid": OPENWEATHER_API_KEY, "units": "metric"}
    r = requests.get(url, params=params, timeout=8)
    if r.status_code != 200:
        return None
    return r.json()

def _get_country_info_by_code(alpha2):
    """Use restcountries to fetch country info by ISO alpha-2 code (no key required)."""
    try:
        url = f"https://restcountries.com/v3.1/alpha/{alpha2}"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()[0]
        return data
    except Exception:
        return None

def _wiki_summary_and_attractions(city_name, max_attractions=5):
    """Return (summary, [attraction_titles]). Uses the wikipedia package."""
    try:
        wikipedia.set_lang("en")
        search_results = wikipedia.search(city_name, results=5)
        if not search_results:
            return None, []
        page_title = search_results[0]
        summary = wikipedia.summary(page_title, sentences=3, auto_suggest=False)
        attractions = []
        for q in (f"{city_name} attractions", f"Things to do in {city_name}", f"Tourist attractions in {city_name}"):
            res = wikipedia.search(q, results=max_attractions)
            if res:
                for t in res:
                    if t not in attractions and t != page_title:
                        attractions.append(t)
            if len(attractions) >= max_attractions:
                break
        return summary, attractions[:max_attractions]
    except Exception:
        return None, []

# --- Helper to save to Supabase ---
def save_destination_to_supabase(data):
    """Insert destination record into Supabase."""
    try:
        response = supabase.table("destinations1").insert(data).execute()
        print(f"✅ Saved {data['city_name']} to Supabase")
        return response
    except Exception as e:
        print("❌ Error saving to Supabase:", e)

# --- Main public function ---
def get_destination_info(city_name):
    """Fetch destination info via public APIs and return a formatted English string."""
    key = city_name.strip().lower()
    if key in _cache:
        ts, reply = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return reply

    # Step 1: Weather
    weather = _get_weather(city_name)
    if not weather:
        reply = f"Sorry, I couldn't find data for '{city_name}'. Make sure the city name is spelled correctly."
        _cache[key] = (time.time(), reply)
        return reply

    # Step 2: Parse results
    country_code = weather.get("sys", {}).get("country", "")
    temp = weather.get("main", {}).get("temp", "N/A")
    weather_desc = weather.get("weather", [{}])[0].get("description", "N/A")
    coords = weather.get("coord", {})
    lat, lon = coords.get("lat"), coords.get("lon")

    # Step 3: Country info
    country_info = _get_country_info_by_code(country_code) if country_code else None
    if country_info:
        country_name = country_info.get("name", {}).get("common", country_code)
        currencies = country_info.get("currencies", {})
        currency_code = next(iter(currencies.keys())) if currencies else "N/A"
        currency_name = currencies.get(currency_code, {}).get("name", "N/A") if currencies else "N/A"
        timezones = country_info.get("timezones", [])
        timezone = timezones[0] if timezones else "N/A"
    else:
        country_name = country_code or "N/A"
        currency_code = "N/A"
        currency_name = "N/A"
        timezone = "N/A"

    # Step 4: Wikipedia
    summary, attractions = _wiki_summary_and_attractions(city_name)
    summary = summary or "No description available."
    attractions_str = ", ".join(attractions) if attractions else "No attraction data available."

    # Step 5: Build reply
    reply = (
        f"Destination: {weather.get('name', city_name)}\n"
        f"Country: {country_name}\n"
        f"Coordinates: {lat}, {lon}\n"
        f"Standard Time / Timezone: {timezone}\n"
        f"Currency: {currency_code} ({currency_name})\n"
        f"Current Weather: {temp}°C, {weather_desc}\n"
        f"Places to Visit: {attractions_str}\n"
        f"Description (short): {summary}\n"
        f"Travel Tips: Check visa requirements, local covid/travel rules, and local transport options.\n"
    )

    # Step 6: Save to Supabase ✅
    record = {
        "city_name": weather.get("name", city_name),
        "country_name": country_name,
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "currency_code": currency_code,
        "currency_name": currency_name,
        "temperature_celsius": temp,
        "weather_description": weather_desc,
        "places_to_visit": attractions,
        "summary": summary,
        "travel_tips": "Check visa requirements, local covid/travel rules, and local transport options."
    }
    save_destination_to_supabase(record)

    _cache[key] = (time.time(), reply)
    return reply
