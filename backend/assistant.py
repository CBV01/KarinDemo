import json
import logging
from datetime import datetime
from libsql_client import Client # type: ignore
from grok_service import GrokService # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Assistant")

class AIAssistant:
    def __init__(self, db: Client):
        self.db = db
        self.grok = GrokService(db)

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
        await self.log_interaction(agent_id, "whatsapp", "outbound", msg)
        
        # In a real app, we'd call the Twilio/WhatsApp API here
        logger.info(f"Notification sent to Agent {agent_id} via WhatsApp:\n{msg}")
        return msg

    async def handle_agent_reply(self, agent_id: str, content: str):
        """
        Handles incoming WhatsApp/Telegram message from the agent (Karin).
        Parses commands and returns a natural language response.
        """
        content_lower = content.strip().lower()
        
        # Log the inbound interaction
        await self.log_interaction(agent_id, "phone", "inbound", content)

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

        # 5. Grok Fallback (Thinking mode)
        else:
            print(f"Grok pondering: {content}")
            return await self.grok.get_response(agent_id, content)

    async def log_interaction(self, agent_id: str, channel: str, direction: str, content: str):
        sql = "INSERT INTO interaction_logs (id, agent_id, channel, direction, content) VALUES (?, ?, ?, ?, ?)"
        from uuid import uuid4
        import uuid
        await self.db.execute(sql, (str(uuid4()), agent_id, channel, direction, content))

# Usage Example (can be triggered by a CRON job at 8:30 AM)
# async def run_morning_cron(db):
#     assistant = AIAssistant(db)
#     await assistant.send_daily_briefing()
