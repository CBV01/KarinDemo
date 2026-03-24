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
        
        system_content = """You are Karin's Real Estate System Controller. You are an expert assistant that manages her CRM.
RULES:
1. TONE: Professional & highly conversational. GREET ONLY AT THE START of a session.
2. DATA INTEGRITY (CRITICAL): NEVER guess email addresses (e.g., joseph.abraham@example.com). If Karin asks to send an email or perform an action, you MUST use the `search_crm` tool first. Once you find the real record, you MUST use the EXACT email found in the tool output (e.g. codebyvictor02@gmail.com).
3. SEARCH BEFORE ACTION: If a name is mentioned (Joseph, Stephen, etc.), you MUST search for them first to get their real Identity/Email.
4. IDENTITY LOCK: If the search results show a real email, that is the ONLY email you are allowed to use for the `send_email` tool.
5. ONLY confirm actions once a tool returns success."""

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
