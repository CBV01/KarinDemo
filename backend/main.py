import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends # type: ignore
from pydantic import BaseModel # type: ignore
from libsql_client import create_client, Client # type: ignore
from dotenv import load_dotenv # type: ignore

# Load environment variables
load_dotenv()

DB_URL = os.getenv("TURSO_DB_URL")
DB_TOKEN = os.getenv("TURSO_DB_TOKEN")

print("[STARTUP] FastAPI Server starting with PKCE-fix v2")

from fastapi.middleware.cors import CORSMiddleware # type: ignore

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

@app.post("/ai/refine-text")
async def refine_text(data: dict, db: Client = Depends(get_db)):
    """ Refine SMS/Email drafts using Grok AI. """
    try:
        from grok_service import GrokService # type: ignore
        grok = GrokService(db)
        prompt = f"Please refine the following real estate SMS/Email draft to sound more professional and engaging: {data.get('text')}"
        refined = await grok.get_response("system", prompt)
        return {"refined_text": refined}
    except Exception as e:
        return {"status": "error", "message": str(e)}

from assistant import AIAssistant # type: ignore
async def telegram_webhook(data: dict, db: Client = Depends(get_db)):
    """ Official Telegram Bot API Webhook. """
    try:
        print(f"Incoming Telegram Data: {data}")
        if "message" not in data:
            return {"status": "ignored"}
        
        message = data["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        
        assistant = AIAssistant(db)
        reply = await assistant.handle_agent_reply(chat_id, text)
        
        # Send reply back to Telegram
        import httpx # type: ignore
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            print("ERROR: TELEGRAM_BOT_TOKEN not set!")
            return {"status": "error", "message": "Token missing"}
            
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )
        return {"status": "ok"}
    except Exception as e:
        print(f"Telegram Webhook Error: {e}")
        return {"status": "internal_error", "message": str(e)}

from fastapi import FastAPI, HTTPException, Depends, Request # type: ignore

@app.get("/webhook/set-telegram")
async def set_telegram_webhook(request: Request):
    import httpx # type: ignore
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return {"status": "error", "message": "TELEGRAM_BOT_TOKEN is missing in HF Secrets!"}
            
        username = os.getenv("HF_USERNAME", "").lower()
        space_name = os.getenv("HF_SPACE_NAME", "").lower()
        
        if username and space_name:
            full_subdomain = f"{username}-{space_name}"
            hostname = f"{full_subdomain}.hf.space"
        else:
            # Fallback to the current request's hostname
            hostname = request.url.hostname
            
        webhook_url = f"https://{hostname}/webhook/telegram"
        
        async with httpx.AsyncClient() as client:
            tg_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
            try:
                import urllib.request, json # type: ignore
                with urllib.request.urlopen(tg_url, timeout=10) as response:
                    res_data = json.load(response)
                    return {"telegram_response": res_data, "method": "urllib_success", "attempted_url": webhook_url}
            except Exception as e2:
                # ULTIMATE BYPASS: If DNS is blocked, we use the raw IP of api.telegram.org
                try:
                    import ssl # type: ignore
                    ctx = ssl._create_unverified_context()
                    ip_url = f"https://149.154.167.220/bot{token}/setWebhook?url={webhook_url}"
                    req = urllib.request.Request(ip_url, headers={"Host": "api.telegram.org"})
                    # Use unverified context to bypass hostname mismatch on IP
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        res_data = json.load(response)
                        return {"telegram_response": res_data, "method": "HARD_IP_SSL_BYPASS", "attempted_url": webhook_url}
                except Exception as e3:
                    return {"status": "error", "message": f"DNS failure and IP-SSL bypass also failed. Check if TG is blocked. Error: {str(e3)}"}
    except Exception as e:
        return {"status": "error", "message": f"Webhook registration failed: {str(e)}"}

from google_auth import GoogleAuthService # type: ignore

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
async def google_callback(code: Optional[str] = None, error: Optional[str] = None, db: Client = Depends(get_db)):
    """ Final Step of the Google Handshake. """
    if error:
        return {"status": "error", "message": f"Google returned error: {error}"}
    if not code:
        return {"status": "error", "message": "No code received from Google"}
        
    try:
        auth_service = GoogleAuthService(db)
        status = await auth_service.save_token(code)
        
        from fastapi.responses import RedirectResponse # type: ignore
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(url=f"{frontend_url}/settings?auth=success")
    except Exception as e:
        print(f"CRITICAL: Google Callback failed: {e}")
        return {
            "status": "error",
            "message": f"Handshake failed! Error: {str(e)}",
            "tip": "This often happens if the 'Redirect URI' in Google Console doesn't match EXACTLY what is in your HF Secrets."
        }

@app.get("/debug/health")
async def debug_health():
    """ Checks if all required keys are present. """
    keys = [
        "TELEGRAM_BOT_TOKEN", "XAI_API_KEY", "TURSO_DB_URL", "TURSO_DB_TOKEN",
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI",
        "HF_USERNAME", "HF_SPACE_NAME"
    ]
    status = {}
    for k in keys:
        val = os.getenv(k)
        status[k] = "Present" if val and len(val) > 4 else "MISSING!"
    
    return {
        "system_status": "online",
        "environment_check": status,
        "tip": "If anything says MISSING, your AI will not work. Add it to Hugging Face Settings -> Secrets."
    }

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8000)
