import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from libsql_client import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Real Estate AI CRM")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database client dependency
async def get_db():
    client = create_client(url=DB_URL, auth_token=DB_TOKEN)
    try:
        yield client
    finally:
        await client.close()

# Pydantic Models
class ClientCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class PropertyCreate(BaseModel):
    client_id: str
    address: str
    purchase_date: str # YYYY-MM-DD

class LeadCreate(BaseModel):
    name: str
    phone: str
    intent: str
    source: str
    property_address: Optional[str] = None
    budget: Optional[str] = None

class AppraisalBook(BaseModel):
    client_id: str
    address: str
    appointment_time: str

@app.get("/")
async def root():
    return {"message": "Real Estate AI CRM API is running"}

# --- Clients Endpoints ---

@app.post("/clients")
async def create_client_endpoint(client_data: ClientCreate, db: Client = Depends(get_db)):
    client_id = str(uuid.uuid4())
    sql = "INSERT INTO clients (id, full_name, email, phone, notes) VALUES (?, ?, ?, ?, ?)"
    params = (client_id, client_data.full_name, client_data.email, client_data.phone, client_data.notes)
    
    try:
        await db.execute(sql, params)
        return {"id": client_id, "message": "Client created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating client: {e}")

@app.get("/clients")
async def get_clients(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM clients")
    return [dict(zip(result.columns, row)) for row in result.rows]

# --- Properties Endpoints ---

@app.post("/properties")
async def create_property(prop_data: PropertyCreate, db: Client = Depends(get_db)):
    prop_id = str(uuid.uuid4())
    # Calculate next anniversary (simplified logic for now)
    sql = "INSERT INTO properties (id, client_id, address, purchase_date) VALUES (?, ?, ?, ?)"
    params = (prop_id, prop_data.client_id, prop_data.address, prop_data.purchase_date)
    
    try:
        await db.execute(sql, params)
        return {"id": prop_id, "message": "Property added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding property: {e}")

@app.get("/properties")
async def get_properties(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM properties")
    return [dict(zip(result.columns, row)) for row in result.rows]

# --- Anniversary Engine (Manual Trigger for Testing) ---

@app.get("/check-anniversaries")
async def check_anniversaries(db: Client = Depends(get_db)):
    # Today's MM-DD
    from datetime import datetime
    today_mm_dd = datetime.now().strftime("%m-%d")
    
    # Query for anniversaries (SQLite/libSQL syntax)
    # purchase_date is YYYY-MM-DD
    sql = "SELECT p.*, c.full_name, c.email, c.phone FROM properties p JOIN clients c ON p.client_id = c.id WHERE strftime('%m-%d', p.purchase_date) = ?"
    result = await db.execute(sql, (today_mm_dd,))
    
    anniversaries = [dict(zip(result.columns, row)) for row in result.rows]
    return {"today_anniversaries": anniversaries, "count": len(anniversaries)}

@app.get("/leads")
async def get_leads(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM leads ORDER BY created_at DESC")
    return [dict(zip(result.columns, row)) for row in result.rows]

@app.get("/interactions")
async def get_interactions(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM interaction_logs ORDER BY created_at DESC LIMIT 20")
    return [dict(zip(result.columns, row)) for row in result.rows]

@app.post("/leads")
async def create_lead(lead: LeadCreate, db: Client = Depends(get_db)):
    lead_id = str(uuid.uuid4())
    sql = "INSERT INTO leads (id, name, phone, intent, source, property_address, budget) VALUES (?, ?, ?, ?, ?, ?, ?)"
    params = (lead_id, lead.name, lead.phone, lead.intent, lead.source, lead.property_address, lead.budget)
    try:
        await db.execute(sql, params)
        # Log automation start
        await db.execute("INSERT INTO interaction_logs (id, channel, direction, content) VALUES (?, ?, ?, ?)",
                         (str(uuid.uuid4()), "system", "outbound", f"Automation sequence initialized for {lead.name}"))
        return {"id": lead_id, "message": "Lead captured and automation sequence initialized"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bulk-import")
async def bulk_import(data: List[dict], db: Client = Depends(get_db)):
    """Simplified bulk import handler"""
    count = 0
    for record in data:
        client_id = str(uuid.uuid4())
        await db.execute("INSERT INTO clients (id, full_name, email, phone) VALUES (?, ?, ?, ?)",
                         (client_id, record.get('name'), record.get('email'), record.get('phone')))
        if record.get('address'):
            await db.execute("INSERT INTO properties (id, client_id, address, purchase_date) VALUES (?, ?, ?, ?)",
                             (str(uuid.uuid4()), client_id, record.get('address'), record.get('date', '2020-01-01')))
        count += 1
    return {"message": f"Successfully imported {count} nodes into the matrix"}

@app.post("/appraisals/book")
async def book_appraisal(data: AppraisalBook, db: Client = Depends(get_db)):
    # Mocking booking logic
    await db.execute("INSERT INTO interaction_logs (id, channel, direction, content) VALUES (?, ?, ?, ?)",
                     (str(uuid.uuid4()), "system", "internal", f"Physical appraisal booked for {data.address} at {data.appointment_time}"))
    return {"message": "Appraisal successfully synced to calendar nodes"}

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from assistant import AIAssistant

@app.get("/assistant/morning-briefing")
async def morning_briefing(db: Client = Depends(get_db)):
    assistant = AIAssistant(db)
    msg = await assistant.send_daily_briefing()
    return {"message": "Morning briefing sent", "content": msg}

@app.post("/webhook/agent")
async def agent_webhook(data: dict, db: Client = Depends(get_db)):
    """
    Real-world webhook intended for Twilio (WhatsApp) or Telegram Bot API.
    Expected data: {"from": "+123456789", "content": "text message"}
    """
    # Verify the agent (simplified)
    # In production, check sender's phone number against a user profile
    content = data.get("content", "")
    agent_id = data.get("agent_id", "karen")
    
    assistant = AIAssistant(db)
    response = await assistant.handle_agent_reply(agent_id, content)
    
    # Return response as JSON (In a real Twilio webhook, you'd return TwiML XML)
    return {"message": response}

from google_auth import GoogleAuthService

@app.get("/auth/login")
async def google_login(db: Client = Depends(get_db)):
    auth_service = GoogleAuthService(db)
    url = auth_service.get_auth_url()
    return {"url": url}

@app.get("/auth/status")
async def google_status(db: Client = Depends(get_db)):
    auth_service = GoogleAuthService(db)
    creds = await auth_service.get_creds()
    return {"connected": creds is not None}

@app.get("/auth/callback")
async def google_callback(code: str, db: Client = Depends(get_db)):
    auth_service = GoogleAuthService(db)
    await auth_service.save_token(code)
    # Redirect back to frontend
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="http://localhost:5173/settings?auth=success")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
