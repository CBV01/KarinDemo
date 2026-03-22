import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

async def check_chat_history():
    if not DB_URL or not DB_TOKEN:
        print("TURSO_DB_URL or TURSO_DB_TOKEN not set")
        return
    
    client = create_client(url=DB_URL, auth_token=DB_TOKEN)
    try:
        result = await client.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT 5")
        for row in result.rows:
            print(dict(zip(result.columns, row)))
    except Exception as e:
        print(f"Error checking chat_history: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_chat_history())
