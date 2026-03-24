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
        if not self.client:
            return "❌ Groq brain error: GROQ_API_KEY is missing in HF Secrets!"

        # 1. Fetch history from Turso
        history_sql = "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT 10"
        result = await self.db.execute(history_sql, (user_id,))
        
        system_content = """You are Karin's Real Estate System Controller. You are an expert assistant that manages her CRM.
RULES:
1. BE CONVERSATIONAL: Start with a warm greeting (e.g., "Hi Karin! How can I help you today?").
2. DATA SEARCH PRIORITY: If Karin asks for details about a person, property, or specific record, ALWAYS use the `search_crm` tool first.
3. INTERACTIVE DATA ENTRY: If Karin wants to add a lead, provide conversational help.
4. ONLY EXECUTE when you have the required information.
5. ONLY confirm actions you actually took using a tool.
6. Your tone is professional and highly conversational. You are her right-hand assistant."""

        if context:
            system_content += f"\n\nCURRENT SYSTEM REAL-TIME DATA:\n{context}\n\nUse this data to make decisions. If the user asks for updates, refer to this."
            
        messages = [{"role": "system", "content": system_content}]
        
        for row in result.rows:
            messages.append({"role": row[0], "content": row[1]})
            
        messages.append({"role": "user", "content": message})

        try:
            # 2. Call Groq API with Tool Support
            completion = self.client.chat.completions.create(
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
            
            # 3. Save to History
            await self.save_message(user_id, "user", message)
            await self.save_message(user_id, "assistant", ai_reply)
            
            return ai_reply

        except Exception as e:
            print(f"Groq API Error: {e}")
            return f"I'm having trouble connecting to my brain (Groq) right now. Error: {str(e)}"

    async def save_message(self, user_id: str, role: str, content: str):
        sql = "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)"
        await self.db.execute(sql, (user_id, role, content))
