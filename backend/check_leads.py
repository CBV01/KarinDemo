import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

async def check():
    url = os.getenv("TURSO_DB_URL")
    token = os.getenv("TURSO_DB_TOKEN")
    client = create_client(url, auth_token=token)
    
    try:
        res = await client.execute("SELECT name, purchase_date, created_at FROM leads ORDER BY created_at DESC LIMIT 10")
        for row in res.rows:
            print(f"Name: {row[0]}, PurchaseDate: {row[1]}, CreatedAt: {row[2]}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check())
