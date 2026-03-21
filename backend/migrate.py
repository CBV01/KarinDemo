import os
import libsql_client as l
from dotenv import load_dotenv

# Load from main project root
load_dotenv(dotenv_path="../.env")

db_url = os.getenv("TURSO_DB_URL")
auth_token = os.getenv("TURSO_DB_TOKEN")

if not db_url:
    print(f"TURSO_DB_URL not set in .env: {os.listdir('..')}")
    exit(1)

db = l.create_client_sync(url=db_url, auth_token=auth_token)

print("Starting migration...")

try:
    db.execute("ALTER TABLE leads ADD COLUMN property_address TEXT")
    print("Added property_address")
except Exception as e: print(e)

try:
    db.execute("ALTER TABLE leads ADD COLUMN budget TEXT")
    print("Added budget")
except Exception as e: print(e)

try:
    db.execute("ALTER TABLE leads ADD COLUMN timeline TEXT")
    print("Added timeline")
except Exception as e: print(e)

try:
    db.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'new'")
    print("Added status")
except Exception as e: print(e)

# Update some data
try:
    db.execute("UPDATE leads SET property_address = '123 Ocean Ave', budget = '$1.2M', timeline = 'Immediate', status = 'active' WHERE id = 1")
    db.execute("UPDATE leads SET property_address = '45 Skyline Dr', budget = '$850k', timeline = '3-6 months', status = 'new' WHERE id = 2")
    print("Updated sample data.")
except Exception as e: print(e)

print("Migration complete.")
