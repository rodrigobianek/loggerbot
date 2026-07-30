import os
import pytz

# Bot token
TOKEN = os.getenv("DISCORD_TOKEN")

# Timezone
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# Channel IDs
ADMIN_LOG_CHANNEL_ID = 1531654435573465318
PUBLIC_LOG_CHANNEL_ID = 1531674099708072098

DB_NAME = "database.db"