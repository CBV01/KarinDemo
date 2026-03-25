import os
import asyncio
from libsql_client import create_client_sync
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

if not DB_URL or not DB_TOKEN:
    print("❌ Error: TURSO_DB_URL and TURSO_DB_TOKEN must be set in .env")
    exit(1)

def init_db():
    print(f"Initializing Turso database at {DB_URL}...")
    
    # Create client
    client = create_client_sync(url=DB_URL, auth_token=DB_TOKEN)
    
    # List of table creation SQL statements
    tables = [
        """
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS properties (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            address TEXT NOT NULL,
            purchase_date DATE NOT NULL,
            last_contacted_date DATE,
            appraisal_status TEXT DEFAULT 'none',
            next_anniversary_date DATE,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            intent TEXT, -- 'buyer', 'seller'
            notes TEXT,
            source TEXT, -- 'inbound_call', 'website', 'manual'
            property_address TEXT,
            purchase_date TEXT,
            budget TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS call_campaigns (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active', -- 'active', 'completed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS call_logs (
            id TEXT PRIMARY KEY,
            contact_id TEXT NOT NULL, -- references clients.id or leads.id
            contact_type TEXT NOT NULL, -- 'client', 'lead'
            phone TEXT,
            outcome TEXT, -- 'answered', 'missed', 'interested', 'not_interested'
            transcript TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            contact_id TEXT NOT NULL,
            contact_type TEXT NOT NULL, -- 'client', 'lead'
            type TEXT NOT NULL, -- 'email', 'sms', 'whatsapp'
            content TEXT NOT NULL,
            status TEXT DEFAULT 'sent', -- 'draft', 'sent', 'failed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS follow_up_sequences (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email_delay INTEGER DEFAULT 0, -- minutes
            sms_delay INTEGER DEFAULT 0, -- minutes
            call_delay INTEGER DEFAULT 0, -- hours
            is_active INTEGER DEFAULT 1 -- 0 for false, 1 for true
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS interaction_logs (
            id TEXT PRIMARY KEY,
            agent_id TEXT DEFAULT 'karen',
            channel TEXT NOT NULL, -- 'whatsapp', 'telegram', 'email'
            direction TEXT NOT NULL, -- 'inbound', 'outbound'
            content TEXT,
            metadata TEXT, -- JSON string for extra data
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS user_tokens (
            service TEXT PRIMARY KEY, -- 'google'
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            token_uri TEXT,
            client_id TEXT,
            client_secret TEXT,
            scopes TEXT,
            expiry TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS appraisals (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            address TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    
    try:
        for sql in tables:
            print(f"Executing: {sql.split('(')[0].strip()}")
            client.execute(sql)
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    init_db()
