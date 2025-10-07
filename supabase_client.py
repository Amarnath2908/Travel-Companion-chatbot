import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()  # loads variables from .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL or KEY not set in environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
