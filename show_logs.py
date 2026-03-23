import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = os.getenv("TURSO_DB_URL")
    token = os.getenv("TURSO_DB_TOKEN")
    client = create_client(url=url, auth_token=token)
    try:
        res = await client.execute("SELECT content FROM interaction_logs WHERE channel = 'telegram' AND direction = 'outbound' ORDER BY created_at DESC LIMIT 3")
        for i, row in enumerate(res.rows):
            print(f"--- MESSAGE {i+1} ---")
            print(row[0])
            print("------------------")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
