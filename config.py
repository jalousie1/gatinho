import os
from dotenv import load_dotenv

# Make sure the .env file is loaded
load_dotenv()

TOKEN = os.getenv('TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Add validation to ensure the keys exist
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")
if not WEATHER_API_KEY:
    raise ValueError("WEATHER_API_KEY not found in .env file")