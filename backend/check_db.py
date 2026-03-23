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
        leads = await client.execute("SELECT count(*) from leads")
        clients = await client.execute("SELECT count(*) from clients")
        anniv = await client.execute("""
            SELECT name, purchase_date FROM leads 
            WHERE strftime('%m-%d', purchase_date) = '03-23'
        """)
        
        print(f"Total Leads: {leads.rows[0][0]}")
        print(f"Total Clients: {clients.rows[0][0]}")
        print(f"Today's Matching Leads: {anniv.rows}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check())
