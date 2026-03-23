import pandas as pd # type: ignore
import io
import json
import logging
import os
from datetime import datetime
from uuid import uuid4
from typing import List, Optional, cast
from libsql_client import Client # type: ignore
from groq_service import GroqService # type: ignore
from google_auth import GoogleAuthService # type: ignore
from sms_service import SmsService # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Assistant")

class AIAssistant:
    def __init__(self, db: Client):
        self.db = db
        self.groq = GroqService(db)

    async def handle_document(self, agent_id: str, file_content: bytes, file_name: str):
        """
        Processes an uploaded document (CSV/Excel) and imports leads.
        """
        try:
            if file_name.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            elif file_name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                return "❌ Unsupported file format. Please upload a CSV or Excel file."

            # Normalize columns
            df.columns = [c.lower().strip() for c in df.columns]
            
            imported_count = 0
            for _, row in df.iterrows():
                name = row.get('name') or row.get('full_name') or row.get('client')
                if not name: continue
                
                phone = str(row.get('phone') or row.get('mobile') or "")
                email = str(row.get('email') or "")
                intent = str(row.get('intent') or "buyer")
                notes = str(row.get('notes') or "")
                
                sql = "INSERT INTO leads (id, name, phone, email, intent, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?)"
                await self.db.execute(sql, (str(uuid4()), name, phone, email, intent, notes, "telegram_upload"))
                imported_count += 1

            return f"✅ Successfully imported {imported_count} leads from '{file_name}'!"
        except Exception as e:
            logger.error(f"Error importing leads: {e}")
            return f"❌ Failed to import leads: {str(e)}"

    async def handle_voice(self, agent_id: str, audio_content: bytes):
        """
        Transcribes a voice note and handles it as a text command.
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return "❌ I heard your voice note, but my 'ears' (OpenAI API) aren't configured yet. Please add OPENAI_API_KEY to secrets."

        try:
            from openai import OpenAI # type: ignore
            client = OpenAI(api_key=openai_key)
            
            # OpenAI requires a file object with a name for transcription
            audio_file = io.BytesIO(audio_content)
            audio_file.name = "voice_note.ogg"
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            
            text = transcript.text
            reply = await self.handle_agent_reply(agent_id, text)
            return f"🎙️ I heard: \"{text}\"\n\n{reply}"
        except Exception as e:
            logger.error(f"Error transcribing voice: {e}")
            return f"❌ Error transcribing voice: {str(e)}"

    async def send_daily_briefing(self, agent_id: str = "karen"):
        """
        Gathers today's anniversaries and "Hot Leads" to send to the agent.
        Now specifically asks for review before sending.
        """
        context = await self.get_system_context()
        prompt = (
            "It's 8:30 AM. Write a very brief 'Good morning' briefing for Karin. "
            "Under 3 sentences: 1. State today's anniversary count and lead count. "
            "2. If anniversaries exist, ask: 'Shall I prepare the drafts for review?' "
            "3. If no anniversaries, just ask if she needs anything. Keep it punchy and professional."
        )
        
        msg = await self.groq.get_response(agent_id, prompt, context=context)
        
        # Log the outbound interaction
        await self.log_interaction(agent_id, "telegram", "outbound", msg)
        
        # Send to Telegram
        if agent_id.isdigit() or os.getenv("TELEGRAM_CHAT_ID"):
            target_id = agent_id if agent_id.isdigit() else os.getenv("TELEGRAM_CHAT_ID", "")
            await self.send_telegram_message(target_id, msg)
        
        logger.info(f"Notification sent to Agent {agent_id} via Telegram:\n{msg}")
        return msg

    async def send_telegram_message(self, chat_id: str, text: str):
        import os
        import json
        import urllib.request
        import ssl
        
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token or not chat_id:
            logger.error(f"TELEGRAM_BOT_TOKEN or chat_id missing. chat_id: {chat_id}")
            return
            
        payload = json.dumps({"chat_id": chat_id, "text": text}).encode('utf-8')
        
        # 1. Try standard DNS-based request first
        tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            req = urllib.request.Request(tg_url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info("Telegram reply via DNS successful")
                return
        except Exception as e:
            logger.warning(f"Telegram DNS send failed: {e}. Trying IP bypass...")

        # 2. Try HARD_IP_SSL_BYPASS if DNS fails
        try:
            ip_url = f"https://149.154.167.220/bot{token}/sendMessage"
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(
                ip_url, 
                data=payload, 
                headers={"Host": "api.telegram.org", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                logger.info("Telegram reply via HARD_IP_SSL_BYPASS successful")
        except Exception as e_ip:
            logger.error(f"Telegram HARD_IP_SSL_BYPASS also failed: {e_ip}")

    async def get_system_context(self):
        """
        Gathers current system status to provide context for Groq.
        """
        try:
            # 1. Get today's anniversaries (From both Properties and Leads)
            today_mm_dd = datetime.now().strftime("%m-%d")
            
            # Anniversaries from Properties (Existing Clients)
            anniv_prop_sql = """
                SELECT p.address, c.full_name 
                FROM properties p 
                JOIN clients c ON p.client_id = c.id 
                WHERE strftime('%m-%d', p.purchase_date) = ?
            """
            anniv_prop_res = await self.db.execute(anniv_prop_sql, (today_mm_dd,))
            
            # Anniversaries from Leads (Prospects with known purchase dates)
            anniv_lead_sql = """
                SELECT property_address, name 
                FROM leads 
                WHERE strftime('%m-%d', purchase_date) = ?
            """
            anniv_lead_res = await self.db.execute(anniv_lead_sql, (today_mm_dd,))

            anniversaries = [f"{row[1]} at {row[0]}" for row in anniv_prop_res.rows]
            anniversaries += [f"{row[1]} (Lead) at {row[0]}" for row in anniv_lead_res.rows]

            # 2. Get recent leads (last 24h)
            leads_sql = "SELECT name FROM leads WHERE created_at >= date('now', '-1 day')"
            leads_res = await self.db.execute(leads_sql)
            recent_leads = [row[0] for row in leads_res.rows]

            # 3. Get total counts
            client_count_res = await self.db.execute("SELECT COUNT(*) FROM clients")
            lead_count_res = await self.db.execute("SELECT COUNT(*) FROM leads")
            
            context = f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            context += f"Total Clients in Database: {client_count_res.rows[0][0]}\n"
            context += f"Total Leads in Pipeline: {lead_count_res.rows[0][0]}\n"
            
            if anniversaries:
                context += f"TODAY'S ANNIVERSARIES: {', '.join(anniversaries)}\n"
            else:
                context += "TODAY'S ANNIVERSARIES: None\n"
                
            if recent_leads:
                context += f"NEW LEADS (LAST 24H): {', '.join(recent_leads)}\n"
            else:
                context += "NEW LEADS (LAST 24H): None\n"
                
            return context
        except Exception as e:
            logger.error(f"Error gathering context: {e}")
            return "System status unavailable."

    async def handle_agent_reply(self, agent_id: str, content: str, channel: str = "telegram"):
        """
        Handles incoming message from the agent.
        Uses Groq Tooling to execute actual system actions.
        """
        content_lower = content.strip().lower()
        await self.log_interaction(agent_id, channel, "inbound", content)

        # Define tools for Groq to use
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Sends an email to a client via Gmail.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "body": {"type": "string", "description": "Email content"}
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_sms",
                    "description": "Sends an SMS message via Twilio.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient phone number"},
                            "message": {"type": "string", "description": "SMS content"}
                        },
                        "required": ["to", "message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_lead",
                    "description": "Adds a new lead to the CRM database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Full name of the lead"},
                            "phone": {"type": "string", "description": "Phone number"},
                            "email": {"type": "string", "description": "Email address"},
                            "intent": {"type": "string", "enum": ["buyer", "seller"], "description": "Whether they are a buyer or seller"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_database_summary",
                    "description": "Gets current counts of leads and clients.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scan_for_anniversaries",
                    "description": "Manually triggers a scan of the database to find property anniversaries for today and sends a briefing.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

        context = await self.get_system_context()
        
        # Call Groq
        response = await self.groq.get_response(agent_id, content, context=context, tools=tools)

        # Check if Groq wants to call a tool
        tool_calls = getattr(response, 'tool_calls', None)
        if tool_calls:
            results: List[str] = []
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if func_name == "send_email":
                    google = GoogleAuthService(self.db)
                    tid = await google.send_email(args['to'], args['subject'], args['body'])
                    results.append(f"✅ Email sent to {args['to']} (ID: {tid})")
                    await self.log_interaction(agent_id, "email", "outbound", args['body'], metadata=json.dumps({"thread_id": tid, "recipient": args['to']}))
                
                elif func_name == "send_sms":
                    sms = SmsService()
                    success = await sms.send_sms(args['to'], args['message'])
                    results.append(f"✅ SMS sent to {args['to']}" if success else "❌ SMS failed")
                    await self.log_interaction(agent_id, "sms", "outbound", args['message'])

                elif func_name == "add_lead":
                    sql = "INSERT INTO leads (id, name, phone, email, intent, source) VALUES (?, ?, ?, ?, ?, ?)"
                    lid = str(uuid4())
                    await self.db.execute(sql, (lid, args['name'], args.get('phone', ''), args.get('email', ''), args.get('intent', 'buyer'), channel))
                    results.append(f"✅ Added lead: {args['name']}")

                elif func_name == "scan_for_anniversaries":
                    chat_id = os.getenv("TELEGRAM_CHAT_ID")
                    if chat_id:
                        await self.send_daily_briefing(chat_id)
                        results.append("✅ Manual anniversary scan triggered and sent to Telegram.")
                    else:
                        results.append("❌ Could not trigger scan: TELEGRAM_CHAT_ID missing.")

                elif func_name == "fetch_database_summary":
                    client_count = (await self.db.execute("SELECT COUNT(*) FROM clients")).rows[0][0]
                    lead_count = (await self.db.execute("SELECT COUNT(*) FROM leads")).rows[0][0]
                    results.append(f"Database Summary: {client_count} Clients, {lead_count} Leads.")

            # Ask Groq to summarize the execution
            summary_prompt = f"I executed: {', '.join(results)}. Please give a final conversational confirmation to Karin. IF IT WAS A GREETING ONLY, IGNORE THE SUMMARY AND JUST BE POLITE."
            return await self.groq.get_response(agent_id, summary_prompt, context=context)

        return response

    async def execute_anniversary_emails(self, agent_id: str, dry_run: bool = False):
        """
        Sends or drafts the emails for today's anniversaries.
        If dry_run=True, it returns the content as a string for review.
        """
        try:
            today_mm_dd = datetime.now().strftime("%m-%d")
            sql = """
                SELECT c.full_name, c.email, p.address 
                FROM properties p 
                JOIN clients c ON p.client_id = c.id 
                WHERE strftime('%m-%d', p.purchase_date) = ?
            """
            res = await self.db.execute(sql, (today_mm_dd,))
            anniversaries = [dict(zip(res.columns, row)) for row in res.rows]
            
            if not anniversaries:
                return "No anniversaries found for today."

            google = GoogleAuthService(self.db)
            
            drafts: List[str] = []
            sent_count = 0
            for a in anniversaries:
                if not a['email'] and not dry_run: continue
                
                # Use Groq to generate a highly personalized body
                prompt = f"Write a short, warm anniversary email for {a['full_name']} who bought the property at {a['address']} exactly some years ago today. Keep it under 3 sentences. No placeholders."
                body = await self.groq.get_response("system", prompt)
                subject = f"Happy Anniversary! 🏠 {a['address']}"
                
                if dry_run:
                    drafts.append(f"To: {a['full_name']} ({a['email'] or 'No Email'})\nSubject: {subject}\nBody: {body}\n---")
                else:
                    thread_id = await google.send_email(a['email'], subject, body)
                    metadata = json.dumps({"thread_id": thread_id, "type": "anniversary_email", "recipient": a['email']})
                    await self.log_interaction(agent_id, "email", "outbound", body, metadata=metadata)
                    sent_count += 1
            
            if dry_run:
                return "\n\n".join(drafts)
            
            return f"🚀 Done! I've sent out {sent_count} personalized anniversary emails. I'll monitor for any replies! ✅"
        except Exception as e:
            logger.error(f"Error handling anniversary emails: {e}")
            return f"❌ Failed to process emails: {str(e)}."

    async def check_email_responses(self, agent_id: str):
        """
        Checks for replies to recently sent emails.
        """
        try:
            # Fetch last 10 outbound emails that have a thread_id in metadata
            sql = "SELECT content, metadata FROM interaction_logs WHERE channel = 'email' AND direction = 'outbound' ORDER BY created_at DESC LIMIT 10"
            res = await self.db.execute(sql)
            
            google = GoogleAuthService(self.db)
            
            updates: List[str] = []
            for row in res.rows:
                metadata = json.loads(row[1]) if row[1] else {}
                thread_id = metadata.get("thread_id")
                recipient = metadata.get("recipient")
                
                if thread_id:
                    reply = await google.get_email_updates(thread_id)
                    if reply:
                        updates.append(str(f"📩 Reply from {recipient}: \"{reply}\""))
            
            if not updates:
                return "No new email replies found since my last check. You're all caught up! ☕"
            
            return "🔔 Here are some recent updates on your sent emails:\n\n" + "\n\n".join(updates)
        except Exception as e:
            logger.error(f"Error checking email responses: {e}")
            return "I had some trouble checking your inbox. Please make sure Google Sync is active."

    async def rewrite_content(self, content: str, tone: str = "professional"):
        """
        Uses Groq to rewrite content in a specific tone.
        """
        prompt = f"Rewrite the following message to be more {tone}, keeping the [Tags] like [Name], [Address], etc. intact:\n\n{content}"
        return await self.groq.get_response("system", prompt)

    async def log_interaction(self, agent_id: str, channel: str, direction: str, content: str, metadata: "str | None" = None):
        sql = "INSERT INTO interaction_logs (id, agent_id, channel, direction, content, metadata) VALUES (?, ?, ?, ?, ?, ?)"
        from uuid import uuid4
        await self.db.execute(sql, (str(uuid4()), agent_id, channel, direction, content, metadata))

# Usage Example (can be triggered by a CRON job at 8:30 AM)
# async def run_morning_cron(db):
#     assistant = AIAssistant(db)
#     await assistant.send_daily_briefing()
