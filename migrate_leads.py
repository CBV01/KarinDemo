import os
import asyncio
from libsql_client import create_client
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    url = os.getenv("TURSO_DB_URL")
    token = os.getenv("TURSO_DB_TOKEN")
    
    if not url or not token:
        print("Missing TURSO_DB_URL or TURSO_DB_TOKEN")
        return

    client = create_client(url=url, auth_token=token)
    try:
        print("Adding missing columns to 'leads' table...")
        
        # Add property_address
        try:
            await client.execute("ALTER TABLE leads ADD COLUMN property_address TEXT")
            print("- Added 'property_address'")
        except Exception as e:
            print(f"- 'property_address' might already exist: {e}")

        # Add purchase_date
        try:
            await client.execute("ALTER TABLE leads ADD COLUMN purchase_date TEXT")
            print("- Added 'purchase_date'")
        except Exception as e:
            print(f"- 'purchase_date' might already exist: {e}")

        # Add budget
        try:
            await client.execute("ALTER TABLE leads ADD COLUMN budget TEXT")
            print("- Added 'budget'")
        except Exception as e:
            print(f"- 'budget' might already exist: {e}")

        print("Migration complete!")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
