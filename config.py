import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
DISCORD_WEBHOOK_UPDATES = os.getenv("DISCORD_WEBHOOK_UPDATES", "")
DISCORD_WEBHOOK_LEADS = os.getenv("DISCORD_WEBHOOK_LEADS", "")
DISCORD_WEBHOOK_LOGS = os.getenv("DISCORD_WEBHOOK_LOGS", "")
MAX_LEADS_PER_RUN = int(os.getenv("MAX_LEADS_PER_RUN", "30"))
MIN_STAR_RATING_FOR_OUTREACH = int(os.getenv("MIN_STAR_RATING_FOR_OUTREACH", "3"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
