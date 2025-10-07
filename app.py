import streamlit as st
import re
# Assuming chatbot_logic.py exists and contains get_destination_info and detect_language
from chatbot_logic import get_destination_info, detect_language

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Travel Companion Chatbot", layout="centered")

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
        font-family: 'Inter', sans-serif;
    }
    /* Title styling */
    h1 {
        color: #007bff; /* Blue main color */
        text-align: center;
        margin-bottom: 0.5rem;
    }
    /* Subheader (Chat title) */
    h2 {
        color: #333333;
        border-bottom: 2px solid #ddd;
        padding-bottom: 5px;
        margin-top: 1.5rem;
    }
    /* Custom chat bubbles (default st.chat_message is good, but for reference) */
    /* Assistant bubble color */
    .stChatMessage [data-testid="stChatMessageContent"] {
        border-radius: 12px 12px 12px 0px;
        background-color: #e6f7ff; /* Lighter blue for assistant */
        box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.05);
    }
    /* User bubble color */
    .stChatMessage [data-testid="stChatMessageContent"].stChatMessage {
        border-radius: 12px 12px 0px 12px;
        background-color: #fff0f5; /* Light peach for user */
    }
    /* Input box */
    .stChatInput {
        padding-top: 10px;
        border-top: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🗺️ Travel Companion Chatbot")
st.markdown("Ask about any city or specific info like 'time of Delhi', 'currency of Japan', or 'places to visit in London'!")

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! 👋 I’m your travel companion. Please type a city name or ask for specific info like 'weather in London'."}
    ]
if "last_city" not in st.session_state:
    st.session_state.last_city = None
if "parsed_info" not in st.session_state:
    st.session_state.parsed_info = {} # Cache for last fetched info

# --- Core Helper: Parse the raw info string into a dictionary (Efficiency Improvement) ---
def parse_raw_info(info_text):
    """
    Parses the raw, dense info string (e.g., 'Dest:X Country:Y...') into a key-value dictionary.
    This replaces multiple regex calls with a single parse operation.
    """
    if not info_text:
        return {}
    
    # 1. Define all possible attribute keys to split by (must match get_destination_info output)
    keys = ["Destination", "Country", "Coordinates", "Standard Time / Timezone", 
            "Currency", "Current Weather", "Places to Visit", 
            "Description (short)", "Travel Tips"]
    
    # 2. Create the regex pattern to split based on any of these keys followed by a colon
    # (?=...) is a positive lookahead to split but keep the delimiter (the key)
    pattern = '|'.join([re.escape(k + ":") for k in keys])
    parts = re.split(f"({pattern})", info_text)
    
    parsed_data = {}
    current_key = None

    # 3. Iterate through parts and fill the dictionary
    for part in parts:
        if not part.strip():
            continue

        if part.endswith(":"):
            # This is a key
            current_key = part.rstrip(":").strip()
        elif current_key:
            # This is the value for the preceding key
            parsed_data[current_key] = part.strip()
            current_key = None # Reset for next key-value pair
    
    return parsed_data

# --- Helper: Clean up "Places to Visit" data ---
def clean_places_to_visit(raw_places_string):
    """
    Filters out items from a comma-separated list that look like non-geographical 
    or irrelevant data (e.g., elections, movies).
    """
    if not raw_places_string:
        return "No specific sites listed."
        
    items = [item.strip() for item in raw_places_string.split(',')]
    
    cleaned_items = []
    
    for item in items:
        # Simple heuristic filtering: skip items containing years (like "2024")
        # or common non-location keywords (like "election", "film", "movie")
        if re.search(r'\b\d{4}\b', item) or \
           any(keyword in item.lower() for keyword in ["election", "film", "movie", "race", "title"]):
            continue
        
        # Keep items that look like names or places
        cleaned_items.append(item)
    
    if not cleaned_items:
        return "No specific sites listed."
        
    return ", ".join(cleaned_items)


# --- Helper: Formats full info from dictionary into a readable list (Improved Readability) ---
def format_info_for_chat(parsed_data):
    """
    Takes a parsed dictionary and formats it into a multi-line, readable Markdown list.
    """
    if not parsed_data:
        return "No destination information available."
        
    formatted_output = []
    
    for key, value in parsed_data.items():
        if key in ["Description (short)", "Places to Visit", "Travel Tips"]:
            
            cleaned_value = value
            # Apply cleaning only to Places to Visit
            if key == "Places to Visit":
                cleaned_value = clean_places_to_visit(value)
            
            # Use a heading/separate block for long descriptive fields
            formatted_output.append(f"\n---")
            formatted_output.append(f"**{key}:**\n{cleaned_value}\n")
        else:
            # Use a simple list item for short fields
            formatted_output.append(f"*{key}:* **{value}**")
            
    return "\n".join(formatted_output)

# --- Helper: Extract Specific Field from dictionary ---
def extract_field(parsed_data, field_name):
    """
    Extracts a specific field (e.g., Currency, Weather) from the parsed dictionary.
    """
    if not parsed_data:
        return f"Sorry, I couldn't find {field_name.lower()} information."
        
    # Standardize the field name for lookup
    lookup_key = field_name
    
    if lookup_key in parsed_data:
        value = parsed_data[lookup_key]
        
        # Apply cleaning if the extracted field is Places to Visit
        if lookup_key == "Places to Visit":
            value = clean_places_to_visit(value)
            
        return f"**{field_name}:** {value}"
            
    return f"Sorry, I couldn't find {field_name.lower()} information for that destination."


# --- Display Chat History ---
st.subheader("💬 Chat")
for msg in st.session_state.messages:
    # Use st.chat_message for automatic, clean chat bubble styling and alignment
    with st.chat_message(msg["role"], avatar="✈️" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# --- Chat Input ---
prompt = st.chat_input("Ask about a city or detail (e.g., 'Currency of Paris')…")

if prompt:
    user_input = prompt.strip()
    lower_input = user_input.lower()
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Greeting & Farewell Logic
    greetings = ["hi", "hello", "hey", "hola"]
    farewells = ["bye", "goodbye", "see you", "exit", "quit"]

    if any(word in lower_input for word in greetings):
        bot_reply = "👋 Hello there! Please enter a destination name to get travel information."
    elif any(word in lower_input for word in farewells):
        bot_reply = "😊 Thank you for chatting with me! Have a great journey ahead! ✈️"
    else:
        # --- Detect attribute keywords ---
        fields = {
            "country": "Country",
            "coordinate": "Coordinates",
            "location": "Coordinates",
            "time": "Standard Time / Timezone",
            "timezone": "Standard Time / Timezone",
            "currency": "Currency",
            "weather": "Current Weather",
            "place": "Places to Visit",
            "attraction": "Places to Visit",
            "description": "Description (short)",
            "tip": "Travel Tips"
        }

        found_field = None
        city = None

        # Detect city name in query (like “time of kolkata”)
        match = re.search(r"(?:in|of)\s+([a-zA-Z\s,]+)$", lower_input)
        if match:
            city = match.group(1).strip().title()
        else:
            # Assume the whole input is the city if no specific field is requested
            # Simple check to use the input as the city name
            city = user_input.title() 

        # Detect which field user wants
        for key in fields:
            if key in lower_input:
                found_field = fields[key]
                break

        # --- Fetch data (only fetch if a new city is mentioned or needed) ---
        current_info_is_valid = st.session_state.last_city == city and st.session_state.parsed_info
        
        if not current_info_is_valid or not found_field:
            with st.spinner(f"Fetching travel details for {city}... 🌍"):
                raw_info = get_destination_info(city)
            
            # Parse the raw info string immediately
            parsed_data = parse_raw_info(raw_info)
            
            # Cache the parsed data and city
            st.session_state.last_city = city
            st.session_state.parsed_info = parsed_data
        else:
            # Use cached data if available (Efficiency gain)
            parsed_data = st.session_state.parsed_info


        # --- Language Check and General Error Handling ---
        if not parsed_data:
            # Check for language only if data fetch failed and input was complex
            if detect_language(user_input) != "en":
                bot_reply = "Sorry, I can only respond in English. Please type in English."
            else:
                bot_reply = f"Sorry, I couldn't find data for '{city}'. Make sure the city name is spelled correctly."
        else:
            # --- Format or Extract Data ---
            if found_field:
                # Extract only the requested field from the parsed dictionary
                bot_reply = extract_field(parsed_data, found_field)
            else:
                # Format the entire dictionary into a clean, structured list
                bot_reply = format_info_for_chat(parsed_data)

    # Add to messages and refresh
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.rerun()
    