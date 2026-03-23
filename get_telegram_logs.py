import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

async def get_telegram_outbound():
    if not DB_URL or not DB_TOKEN:
        print("TURSO_DB_URL or TURSO_DB_TOKEN not set")
        return
    
    client = create_client(url=DB_URL, auth_token=DB_TOKEN)
    try:
        # Fetch the last 5 messages sent by the AI to Telegram
        result = await client.execute(
            "SELECT content, created_at FROM interaction_logs WHERE channel = 'telegram' AND direction = 'outbound' ORDER BY created_at DESC LIMIT 5"
        )
        print("\n--- LATEST AI MESSAGES ON TELEGRAM ---\n")
        for row in result.rows:
            print(f"[{row[1]}] AI REPLY:")
            print(f"{row[0]}")
            print("-" * 40)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(get_telegram_outbound())
