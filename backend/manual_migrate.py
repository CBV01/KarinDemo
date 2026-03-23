import os
from libsql_client import create_client_sync
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

def migrate():
    print("Starting manual migration for missing columns...")
    client = create_client_sync(url=DB_URL, auth_token=DB_TOKEN)
    
    try:
        # 1. Add columns to leads table if they don't exist
        columns_to_add = [
            "ALTER TABLE leads ADD COLUMN source TEXT",
            "ALTER TABLE leads ADD COLUMN property_address TEXT",
            "ALTER TABLE leads ADD COLUMN purchase_date TEXT",
            "ALTER TABLE leads ADD COLUMN budget TEXT"
        ]
        
        for sql in columns_to_add:
            try:
                print(f"Executing: {sql}")
                client.execute(sql)
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("--> Column already exists, skipping.")
                else:
                    print(f"--> Error: {e}")
                    
        print("Migration check complete.")
    finally:
        client.close()

if __name__ == "__main__":
    migrate()
