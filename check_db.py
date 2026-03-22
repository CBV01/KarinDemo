import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

async def check_data():
    if not DB_URL or not DB_TOKEN:
        print("TURSO_DB_URL or TURSO_DB_TOKEN not set")
        return
    
    client = create_client(url=DB_URL, auth_token=DB_TOKEN)
    try:
        tables = ['clients', 'leads', 'properties', 'interaction_logs', 'chat_history']
        for table in tables:
            try:
                result = await client.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.rows[0][0]
                print(f"Table {table}: {count} rows")
            except Exception as e:
                print(f"Table {table} error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_data())
