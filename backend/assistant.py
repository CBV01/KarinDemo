import pandas as pd
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
            from openai import OpenAI
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
        """
        # 1. Get anniversaries
        today_mm_dd = datetime.now().strftime("%m-%d")
        anniv_sql = """
            SELECT p.address, c.full_name, c.phone 
            FROM properties p 
            JOIN clients c ON p.client_id = c.id 
            WHERE strftime('%m-%d', p.purchase_date) = ?
        """
        anniv_result = await self.db.execute(anniv_sql, (today_mm_dd,))
        anniversaries = [dict(zip(anniv_result.columns, row)) for row in anniv_result.rows]

        # 2. Get Hot Leads (appraisals requested yesterday)
        # (Simplified query for demo)
        leads_sql = "SELECT name, phone FROM leads WHERE created_at >= date('now', '-1 day')"
        leads_result = await self.db.execute(leads_sql)
        hot_leads = [dict(zip(leads_result.columns, row)) for row in leads_result.rows]

        # Construct message
        msg = f"Good morning Karin! ☕\n\n"
        if anniversaries:
            msg += f"🎉 Today's Anniversaries ({len(anniversaries)}):\n"
            for a in anniversaries:
                msg += f"- {a['full_name']} ({a['address']})\n"
            msg += "\nShall I send the anniversary letters? Reply 'Yes' to send all, or 'Skip [Name]'."
        else:
            msg += "No anniversaries today. 📅\n"

        if hot_leads:
            msg += f"\n🔥 New Leads ({len(hot_leads)}):\n"
            for l in hot_leads:
                msg += f"- {l['name']}\n"
        
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

    async def handle_agent_reply(self, agent_id: str, content: str, channel: str = "telegram"):
        """
        Handles incoming WhatsApp/Telegram message from the agent (Karin).
        Parses commands and returns a natural language response.
        """
        content_lower = content.strip().lower()
        
        # Log the inbound interaction
        await self.log_interaction(agent_id, channel, "inbound", content)

        # 1. Handle "Add Lead" command
        if content_lower.startswith("add lead:"):
            # Format: 'add lead: Name, Phone, Intent'
            try:
                # Use split instead of slicing for better parsing
                _, details = content_lower.split(":", 1)
                parts = [p.strip() for p in details.split(",")]
                name = parts[0]
                phone = parts[1] if len(parts) > 1 else ""
                intent = parts[2] if len(parts) > 2 else "buyer"
                
                from uuid import uuid4
                sql = "INSERT INTO leads (id, name, phone, intent, source) VALUES (?, ?, ?, ?, ?)"
                await self.db.execute(sql, (str(uuid4()), name, phone, intent, "whatsapp"))
                return f"✅ Done! Added lead '{name}' to your dashboard."
            except Exception as e:
                return "❌ Sorry, I couldn't parse that. Try: 'Add lead: John Doe, 555-0123, seller'"

        # 2. Handle "Anniversaries" request
        elif "anniversary" in content_lower or "anniversaries" in content_lower:
            today_msg = await self.send_daily_briefing(agent_id)
            return f"Here is today's anniversary check:\n{today_msg}"

        # 3. Handle Confirmation for sending letters
        elif content_lower == "yes":
            # In a real app, this would trigger the Email/SMS sequence
            return "Perfect. I'm sending out the property anniversary letters as we speak. 📧✅"

        # 4. Handle "Update" for recent activity
        elif "update" in content_lower or "leads" in content_lower:
            leads_sql = "SELECT name, source FROM leads ORDER BY created_at DESC LIMIT 3"
            res = await self.db.execute(leads_sql)
            recent = [dict(zip(res.columns, row)) for row in res.rows]
            if not recent:
                return "No new leads recently. You're all caught up! 👍"
            msg = "🔥 Recent leads:\n" + "\n".join([f"- {l['name']} ({l['source']})" for l in recent])
            return msg

        # 5. Groq Fallback (Thinking mode)
        else:
            print(f"Groq pondering: {content}")
            return await self.groq.get_response(agent_id, content)

    async def rewrite_content(self, content: str, tone: str = "professional"):
        """
        Uses Groq to rewrite content in a specific tone.
        """
        prompt = f"Rewrite the following message to be more {tone}, keeping the [Tags] like [Name], [Address], etc. intact:\n\n{content}"
        return await self.groq.get_response("system", prompt)

    async def log_interaction(self, agent_id: str, channel: str, direction: str, content: str):
        sql = "INSERT INTO interaction_logs (id, agent_id, channel, direction, content) VALUES (?, ?, ?, ?, ?)"
        from uuid import uuid4
        import uuid
        await self.db.execute(sql, (str(uuid4()), agent_id, channel, direction, content))

# Usage Example (can be triggered by a CRON job at 8:30 AM)
# async def run_morning_cron(db):
#     assistant = AIAssistant(db)
#     await assistant.send_daily_briefing()
