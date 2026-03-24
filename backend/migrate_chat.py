import os
import asyncio
from libsql_client import create_client # type: ignore
from dotenv import load_dotenv # type: ignore

async def migrate():
    load_dotenv()
    url = os.getenv("TURSO_DB_URL")
    token = os.getenv("TURSO_DB_TOKEN")
    
    print(f"Connecting to {url}...")
    client = create_client(url=url, auth_token=token)
    
    table_sql = """
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        print("Executing migration...")
        await client.execute(table_sql)
        print("SUCCESS: Table 'chat_history' created successfully.")
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
