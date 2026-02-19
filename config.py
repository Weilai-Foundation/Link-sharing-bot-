import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "22884130"))
API_HASH = os.getenv("API_HASH", "a69e8b16dac958f1bd31eee360ec53fa")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8276153107:AAHV1SF_rg9OtrXARRF7yOKHBZWmykQ-dko")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Fugui:tianlu@cluster0.6hyrp0r.mongodb.net/?appName=Cluster0")
ADMINS = [int(x) for x in os.getenv("ADMINS", "7840980054").split(",") if x.strip()]
START_PIC = os.getenv("START_PIC", "")
LINK_PIC = os.getenv("LINK_PIC", "")
