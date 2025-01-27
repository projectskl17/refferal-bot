import os

REFERRALS_PER_LEVEL = 5

MONGODB_URL = os.getenv("MONGODB_URL", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

OWNER_ID = int(os.getenv("OWNER_ID", 0))

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))

CHANNELS = list(map(int, os.getenv("CHANNELS", "-1002245937378, -1001711146727").split(',')))
