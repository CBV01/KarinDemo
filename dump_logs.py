import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

async def get_telegram_outbound():
    client = create_client(url=DB_URL, auth_token=DB_TOKEN)
    try:
        result = await client.execute(
            "SELECT content, created_at FROM interaction_logs WHERE channel = 'telegram' AND direction = 'outbound' ORDER BY created_at DESC LIMIT 5"
        )
        with open("telegram_output.txt", "w", encoding="utf-8") as f:
            for row in result.rows:
                f.write(f"[{row[1]}] AI REPLY:\n{row[0]}\n{'-'*40}\n")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(get_telegram_outbound())
