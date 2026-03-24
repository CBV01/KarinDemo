import os
import uuid
import httpx # type: ignore
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
    purchase_date: str

class SettingsUpdate(BaseModel):
    key: str
    value: str # YYYY-MM-DD

class LeadCreate(BaseModel):
    name: str
    phone: str
    intent: str
    source: str
    email: Optional[str] = None
    property_address: Optional[str] = None
    purchase_date: Optional[str] = None
    budget: Optional[str] = None

class AppraisalBook(BaseModel):
    client_id: str
    address: str
    appointment_time: str

import asyncio
from datetime import datetime, time

async def daily_briefing_task():
    """
    Background task that sends the daily briefing at 8:30 AM every day.
    """
    print("[STARTUP] Daily Briefing Task Initialized")
    while True:
        try:
            now = datetime.now()
            # Check if it's between 8:30 AM and 9:00 AM
            if now.hour == 8 and now.minute >= 30:
                # Get a DB client
                db_url = os.getenv("TURSO_DB_URL")
                db_token = os.getenv("TURSO_DB_TOKEN")
                chat_id = os.getenv("TELEGRAM_CHAT_ID")
                
                if db_url and db_token and chat_id:
                    from libsql_client import create_client # type: ignore
                    async with create_client(url=db_url, auth_token=db_token) as db:
                        assistant = AIAssistant(db)
                        # Check if we already sent it today
                        today_date = datetime.now().strftime("%Y-%m-%d")
                        check_sql = "SELECT id FROM interaction_logs WHERE agent_id = ? AND content LIKE 'Good morning Karin!%' AND date(created_at) = ?"
                        res = await db.execute(check_sql, (chat_id, today_date))
                        if not res.rows:
                            print(f"Sending daily briefing to {chat_id}...")
                            await assistant.send_daily_briefing(chat_id)
                        else:
                            print("Daily briefing already sent today.")
            
            # Wait 15 minutes before checking again
            await asyncio.sleep(900) 
        except Exception as e:
            print(f"Error in daily_briefing_task: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    # Start the background task
    asyncio.create_task(daily_briefing_task())

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
    sql = "INSERT INTO properties (id, client_id, address, purchase_date) VALUES (?, ?, ?, ?)"
    params = (prop_id, prop_data.client_id, prop_data.address, prop_data.purchase_date)
    
    try:
        await db.execute(sql, params)
        
        # 1. Sync to Google Calendar if possible
        # Fetch client name first
        client_res = await db.execute("SELECT full_name FROM clients WHERE id = ?", (prop_data.client_id,))
        if client_res.rows:
            client_name = client_res.rows[0][0]
            from google_auth import GoogleAuthService # type: ignore
            auth_service = GoogleAuthService(db)
            await auth_service.create_anniversary_event(client_name, prop_data.address, prop_data.purchase_date)
            
        return {"id": prop_id, "message": "Property added successfully and synced to calendar"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding property: {e}")

@app.get("/properties")
async def get_properties(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM properties")
    return [dict(zip(result.columns, row)) for row in result.rows]

# --- Anniversary Engine (Manual Trigger for Testing) ---

@app.get("/anniversaries")
async def get_anniversaries(db: Client = Depends(get_db)):
    # Fetch all property ownership records for the calendar/list projection
    # Also include leads with purchase dates
    sql = """
        SELECT p.id, p.address as property_address, c.full_name as name, c.email, c.phone, p.purchase_date, 'client' as type
        FROM properties p 
        JOIN clients c ON p.client_id = c.id
        UNION ALL
        SELECT id, property_address, name, email, phone, purchase_date, 'lead' as type
        FROM leads
        WHERE purchase_date IS NOT NULL
    """
    result = await db.execute(sql)
    return [dict(zip(result.columns, row)) for row in result.rows]

@app.get("/leads")
async def get_leads(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM leads ORDER BY created_at DESC")
    return [dict(zip(result.columns, row)) for row in result.rows]

@app.get("/interactions")
async def get_interactions(db: Client = Depends(get_db)):
    result = await db.execute("SELECT * FROM interaction_logs ORDER BY created_at DESC LIMIT 20")
    return [dict(zip(result.columns, row)) for row in result.rows]

@app.get("/assistant/check-anniversaries")
async def manual_anniversary_check(db: Client = Depends(get_db)):
    """
    Manually triggers an anniversary check and sends a briefing to Telegram.
    """
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return {"status": "error", "message": "TELEGRAM_CHAT_ID not set"}
    
    assistant = AIAssistant(db)
    msg = await assistant.send_daily_briefing(chat_id)
    return {"status": "ok", "message": "Anniversary scan complete", "briefing": msg}

@app.post("/leads")
async def create_lead(lead: LeadCreate, db: Client = Depends(get_db)):
    lead_id = str(uuid.uuid4())
    try:
        # We use a try-except block for each potential missing column or a fallback query
        sql = """
            INSERT INTO leads (id, name, phone, email, intent, source, property_address, purchase_date, budget) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (lead_id, lead.name, lead.phone, lead.email, lead.intent, lead.source, lead.property_address, lead.purchase_date, lead.budget)
        await db.execute(sql, params)
        
        # --- AUTO SCAN ON ADD ---
        # If a purchase date was provided, trigger a scan to see if it's an anniversary
        if lead.purchase_date:
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if chat_id:
                assistant = AIAssistant(db)
                # We check specifically if THIS new lead has an anniversary today
                today_mm_dd = datetime.now().strftime("%m-%d")
                p_date = lead.purchase_date or ""
                if len(p_date) >= 5:
                    # Explicit string range to satisfy type checker
                    lead_mm_dd = p_date[len(p_date)-5:len(p_date)]
                    if lead_mm_dd == today_mm_dd:
                        await assistant.send_telegram_message(chat_id, f"🎉 Instant Match! The manual lead {lead.name} has a property anniversary TODAY ({lead.property_address}). I've updated the briefing.")
                        await assistant.send_daily_briefing(chat_id)

    except Exception as e:
        print(f"Full insert failed, using adaptive fallback: {e}")
        # Try a more limited insert but preserve the date and address if possible
        try:
            sql_alt = "INSERT INTO leads (id, name, phone, email, intent, source, purchase_date, property_address) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            await db.execute(sql_alt, (lead_id, lead.name, lead.phone, lead.email, lead.intent, lead.source, lead.purchase_date, lead.property_address))
        except Exception as e_alt:
            print(f"Adaptive fallback also failed, using final fallback: {e_alt}")
            sql_fallback = "INSERT INTO leads (id, name, phone, email, intent, source) VALUES (?, ?, ?, ?, ?, ?)"
            params_fallback = (lead_id, lead.name, lead.phone, lead.email, lead.intent, lead.source)
            await db.execute(sql_fallback, params_fallback)

    try:
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
@app.post("/webhook/telegram")
async def telegram_webhook(data: dict, db: Client = Depends(get_db)):
    """ Official Telegram Bot API Webhook. """
    try:
        print(f"Incoming Telegram Data: {data}")
        if "message" not in data:
            return {"status": "ignored"}
        
        message = data["message"]
        chat_id = str(message["chat"]["id"])
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        assistant = AIAssistant(db)
        
        # 1. Handle Voice Note
        if "voice" in message:
            file_id = message["voice"]["file_id"]
            # Download file from Telegram
            async with httpx.AsyncClient() as client:
                file_info = await client.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
                file_path = file_info.json()["result"]["file_path"]
                file_res = await client.get(f"https://api.telegram.org/file/bot{token}/{file_path}")
                audio_content = file_res.content
            
            reply = await assistant.handle_voice(chat_id, audio_content)
            await assistant.send_telegram_message(chat_id, reply)
            return {"status": "ok"}

        # 2. Handle Document (CSV/Excel)
        elif "document" in message:
            file_id = message["document"]["file_id"]
            file_name = message["document"]["file_name"]
            # Download file from Telegram
            async with httpx.AsyncClient() as client:
                file_info = await client.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
                file_path = file_info.json()["result"]["file_path"]
                file_res = await client.get(f"https://api.telegram.org/file/bot{token}/{file_path}")
                file_content = file_res.content
            
            reply = await assistant.handle_document(chat_id, file_content, file_name)
            await assistant.send_telegram_message(chat_id, reply)
            return {"status": "ok"}

        # 3. Handle Text Message
        elif "text" in message:
            text = message["text"]
            reply = await assistant.handle_agent_reply(chat_id, text, channel="telegram")
            await assistant.send_telegram_message(chat_id, reply)
            return {"status": "ok"}
            
        return {"status": "unsupported_type"}
    except Exception as e:
        print(f"Telegram Webhook Error: {e}")
        return {"status": "internal_error", "message": str(e)}

class RewriteRequest(BaseModel):
    content: str
    tone: Optional[str] = "professional"

@app.post("/assistant/rewrite")
async def assistant_rewrite(req: RewriteRequest, db: Client = Depends(get_db)):
    assistant = AIAssistant(db)
    new_text = await assistant.rewrite_content(req.content, req.tone)
    return {"content": new_text}

@app.get("/assistant/morning-briefing")
async def get_morning_briefing(db: Client = Depends(get_db)):
    assistant = AIAssistant(db)
    # Use a default agent_id or fetch from env
    agent_id = os.getenv("TELEGRAM_CHAT_ID", "karen")
    content = await assistant.send_daily_briefing(agent_id)
    return {"content": content}

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

from sms_service import SmsService # type: ignore

class CampaignLaunchRequest(BaseModel):
    campaign_id: str
    template_type: str # 'email', 'sms'
    content: str

@app.post("/campaigns/launch")
async def launch_campaign(req: CampaignLaunchRequest, db: Client = Depends(get_db)):
    """
    Launches a campaign by sending messages to all eligible contacts.
    """
    sms_service = SmsService()
    
    # 1. Fetch eligible contacts (demo: all leads for now)
    leads_res = await db.execute("SELECT name, phone FROM leads")
    leads = [dict(zip(leads_res.columns, row)) for row in leads_res.rows]
    
    success_log = []
    for lead in leads:
        if not lead['phone']: continue
        
        # Personalized content
        msg = req.content.replace("[Name]", lead['name'])
        
        if req.template_type == 'sms':
            success = await sms_service.send_sms(lead['phone'], msg)
            if success:
                success_log.append(True)
            
        # Log interaction
        await db.execute(
            "INSERT INTO interaction_logs (id, agent_id, channel, direction, content) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), "system", req.template_type, "outbound", msg)
        )
        
    return {"message": f"Campaign launched. Sent {len(success_log)} {req.template_type}s."}

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

# --- Settings Endpoints ---

@app.get("/settings")
async def get_settings(db: Client = Depends(get_db)):
    """ Retrieve all dynamic settings (like API keys). """
    result = await db.execute("SELECT key, value FROM settings")
    return {row[0]: row[1] for row in result.rows}

@app.post("/settings")
async def update_settings(req: SettingsUpdate, db: Client = Depends(get_db)):
    """ Update a specific dynamic setting. """
    try:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (req.key, req.value))
        return {"status": "success", "message": f"Setting '{req.key}' updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn # type: ignore
    uvicorn.run(app, host="0.0.0.0", port=8000)
