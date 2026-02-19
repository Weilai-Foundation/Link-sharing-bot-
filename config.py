import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
START_PIC = os.getenv("START_PIC", "")
LINK_PIC = os.getenv("LINK_PIC", "")
