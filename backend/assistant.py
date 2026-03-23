import pandas as pd # type: ignore
import io
import json
import logging
import os
from datetime import datetime
from uuid import uuid4
from libsql_client import Client # type: ignore
from groq_service import GroqService # type: ignore

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
        Gathers today's anniversaries and "Hot Leads" to send to the agent via Groq for natural language.
        """
        context = await self.get_system_context()
        prompt = "It's 8:30 AM. Write a proactive 'Good morning' briefing for Karin. Summarize today's anniversaries and any new leads from the last 24h. Be professional, friendly, and ask if she wants you to handle anything (like sending anniversary letters)."
        
        msg = await self.groq.get_response(agent_id, prompt, context=context)
        
        # Log the outbound interaction
        await self.log_interaction(agent_id, "telegram", "outbound", msg)
        
        # Send to Telegram if agent_id looks like a chat_id
        if agent_id.isdigit():
            await self.send_telegram_message(agent_id, msg)
        
        logger.info(f"Notification sent to Agent {agent_id} via Telegram:\n{msg}")
        return msg

    async def send_telegram_message(self, chat_id: str, text: str):
        import os
        import json
        import urllib.request
        import ssl
        
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
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
            # 1. Get today's anniversaries
            today_mm_dd = datetime.now().strftime("%m-%d")
            anniv_sql = """
                SELECT p.address, c.full_name 
                FROM properties p 
                JOIN clients c ON p.client_id = c.id 
                WHERE strftime('%m-%d', p.purchase_date) = ?
            """
            anniv_res = await self.db.execute(anniv_sql, (today_mm_dd,))
            anniversaries = [f"{row[1]} at {row[0]}" for row in anniv_res.rows]

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
        Handles incoming WhatsApp/Telegram message from the agent (Karin).
        Parses commands and returns a natural language response.
        """
        content_lower = content.strip().lower()
        
        # Log the inbound interaction
        await self.log_interaction(agent_id, channel, "inbound", content)

        # 1. Handle "Add Lead" command (Still hardcoded for precision)
        if content_lower.startswith("add lead:"):
            try:
                _, details = content.split(":", 1)
                parts = [p.strip() for p in details.split(",")]
                name = parts[0]
                phone = parts[1] if len(parts) > 1 else ""
                intent = parts[2] if len(parts) > 2 else "buyer"
                
                sql = "INSERT INTO leads (id, name, phone, intent, source) VALUES (?, ?, ?, ?, ?)"
                await self.db.execute(sql, (str(uuid4()), name, phone, intent, channel))
                return f"✅ Done! Added lead '{name}' to your dashboard."
            except Exception as e:
                return "❌ Sorry, I couldn't parse that. Try: 'Add lead: John Doe, 555-0123, seller'"

        # 2. Handle "send messages" for anniversaries (the interactive flow)
        if "send" in content_lower and ("message" in content_lower or "email" in content_lower or "anniversaries" in content_lower):
            context = await self.get_system_context()
            if "TODAY'S ANNIVERSARIES: None" in context:
                return "You're all caught up! There are no property anniversaries to send messages for today. 🏠✅"
            
            prompt = "The user wants to send anniversary messages. Based on the today's anniversaries in the context, write a personalized email for EACH one. Keep them professional but warm. Present them clearly so I can ask for confirmation. Use [Name] and [Address] tags."
            return await self.groq.get_response(agent_id, prompt, context=context)

        # 3. Handle "confirm" / "send them" / "go ahead"
        if any(word in content_lower for word in ["confirm", "send them", "go ahead", "send all", "yes send"]):
            return await self.execute_anniversary_emails(agent_id)

        # 4. Handle "updates" / "responses"
        if "update" in content_lower or "response" in content_lower or "reply" in content_lower:
            return await self.check_email_responses(agent_id)

        # 5. Conversational Logic via Groq with System Context
        context = await self.get_system_context()
        
        # If it's a greeting or start command, inject a welcome prompt
        if content_lower in ["hello", "hi", "hey", "/start", "start"]:
            prompt = f"The user said '{content}'. Introduce yourself as Karin's AI Personal Assistant. Mention that you're ready to help manage her real estate business. Based on the context provided, give her a quick summary of what's happening today (anniversaries/leads) and ask what she'd like to do."
            return await self.groq.get_response(agent_id, prompt, context=context)

        # Default: Let Groq handle it with the current context
        return await self.groq.get_response(agent_id, content, context=context)

    async def execute_anniversary_emails(self, agent_id: str):
        """
        Actually sends the emails for today's anniversaries.
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
                return "No anniversaries found to send."

            from google_auth import GoogleAuthService # type: ignore
            google = GoogleAuthService(self.db)
            
            sent_count = 0
            for a in anniversaries:
                if not a['email']: continue
                
                # Use Groq to generate a highly personalized body for this specific anniversary
                prompt = f"Write a short, warm anniversary email for {a['full_name']} who bought the property at {a['address']} exactly some years ago today. Keep it under 3 sentences. No placeholders like [Name], use the real names."
                body = await self.groq.get_response("system", prompt)
                subject = f"Happy Anniversary! 🏠 {a['address']}"
                
                thread_id = await google.send_email(a['email'], subject, body)
                
                # Log it with the thread_id for tracking
                metadata = json.dumps({"thread_id": thread_id, "type": "anniversary_email", "recipient": a['email']})
                await self.log_interaction(agent_id, "email", "outbound", body, metadata=metadata)
                sent_count += 1
            
            return f"🚀 Done! I've sent out {sent_count} personalized anniversary emails. I'll monitor for any replies and let you know! ✅"
        except Exception as e:
            logger.error(f"Error sending anniversary emails: {e}")
            return f"❌ Failed to send emails: {str(e)}. Make sure your Google account is connected in Settings!"

    async def check_email_responses(self, agent_id: str):
        """
        Checks for replies to recently sent emails.
        """
        try:
            # Fetch last 10 outbound emails that have a thread_id in metadata
            sql = "SELECT content, metadata FROM interaction_logs WHERE channel = 'email' AND direction = 'outbound' ORDER BY created_at DESC LIMIT 10"
            res = await self.db.execute(sql)
            
            from google_auth import GoogleAuthService # type: ignore
            google = GoogleAuthService(self.db)
            
            updates = []
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
