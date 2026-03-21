import os
import uuid
from libsql_client import create_client_sync
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

def seed():
    client = create_client_sync(url=DB_URL, auth_token=DB_TOKEN)
    
    # 1. Create a client
    client_id = str(uuid.uuid4())
    client.execute("INSERT INTO clients (id, full_name, email, phone) VALUES (?, ?, ?, ?)", 
                   (client_id, "The Smiths", "smith@email.com", "+123456789"))
    
    # 2. Add property with TODAY as anniversary
    from datetime import datetime
    today = datetime.now()
    purchase_date = f"{today.year - 5}-{today.strftime('%m-%d')}"
    client.execute("INSERT INTO properties (id, client_id, address, purchase_date, appraisal_status) VALUES (?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), client_id, "4602 Pink Sand Road", purchase_date, "none"))
    
    # 3. Add a Lead
    client.execute("INSERT INTO leads (id, name, phone, intent, source) VALUES (?, ?, ?, ?, ?)",
                   (str(uuid.uuid4()), "Sarah Marshall", "+987654321", "seller", "website"))

    print("Seeding complete! Added 1 client, 1 anniversary property, and 1 lead.")
    client.close()

if __name__ == "__main__":
    seed()
