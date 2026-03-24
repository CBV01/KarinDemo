import os
import json
from typing import List, Dict, Optional
from groq import Groq # type: ignore

class GroqService:
    def __init__(self, db_client):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.db = db_client
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    async def get_response(self, user_id: str, message: str, context: str = "", tools: Optional[List[Dict]] = None) -> str:
        # Check for dynamic API key in settings
        settings_res = await self.db.execute("SELECT value FROM settings WHERE key = 'groq_api_key'")
        current_key = settings_res.rows[0][0] if settings_res.rows else self.api_key

        if not current_key:
            return "❌ Groq brain error: GROQ_API_KEY is missing! Update it in Settings."

        # Re-initialize client if key is different from original env key
        dynamic_client = Groq(api_key=current_key) if current_key else self.client
        if not dynamic_client:
            return "❌ Groq brain failure: Missing API client."

        # 1. Fetch history from Turso (Last 20 messages)
        history_sql = "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT 20"
        result = await self.db.execute(history_sql, (user_id,))
        
        system_content = """You are Karin's Real Estate Relationship Manager. Your primary goal is to RE-ENGAGE PAST CLIENTS and nurture them using their property purchase history.
STRATEGY:
1. NURTURE-FIRST: These are people Karin has dealt with before. Be warm, professional, and focus on their property history.
2. ANNIVERSARY TRIGGER: Property anniversaries are the CORE of your business. Use them as an excuse to send a valuation update or a friendly check-in.
3. CONTEXT: If you see a `property_address` or `purchase_date`, use it to personalize your conversation (e.g. "Hi Sarah, how has life been at 123 Main St since you bought it in 2022?").
4. OBJECTIVE: We want to see if they want to SELL their current home or if they've bought elsewhere and need another valuation.
5. PREVIEW CAMPAIGNS: Always show David the drafts of Emails/SMS first for approval.
6. TOOL SYNTAX: Use valid JSON. ONLY confirm actions once tools return success. David is the AGENT, not a lead."""

        if context:
            system_content += f"\n\nCURRENT SYSTEM REAL-TIME DATA:\n{context}\n\nUse this data to make decisions. If the user asks for updates, refer to this."
            
        messages = [{"role": "system", "content": system_content}]
        
        for row in result.rows:
            messages.append({"role": row[0], "content": row[1]})
            
        messages.append({"role": "user", "content": message})

        try:
            # 2. Call Groq API with Tool Support
            completion = dynamic_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0,
                max_tokens=1024,
                top_p=1,
                stream=False,
            )
            
            response_message = completion.choices[0].message
            
            # Handle Tool Calls if any
            if response_message.tool_calls:
                return response_message # Return the full message object to be handled by Assistant
            
            ai_reply = response_message.content
            
            return ai_reply

        except Exception as e:
            print(f"Groq API Error: {e}")
            return f"I'm having trouble connecting to my brain (Groq) right now. Error: {str(e)}"
