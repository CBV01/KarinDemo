import os
import json
from typing import List, Dict
from groq import Groq

class GroqService:
    def __init__(self, db_client):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.db = db_client
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None

    async def get_response(self, user_id: str, message: str) -> str:
        if not self.client:
            return "❌ Groq brain error: GROQ_API_KEY is missing in HF Secrets!"

        # 1. Fetch history from Turso
        history_sql = "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT 10"
        result = await self.db.execute(history_sql, (user_id,))
        
        messages = [{"role": "system", "content": "You are Karin's Real Estate AI Assistant. Help her manage leads, anniversaries, and campaigns. Keep it professional but friendly."}]
        
        for row in result.rows:
            messages.append({"role": row[0], "content": row[1]})
            
        messages.append({"role": "user", "content": message})

        try:
            # 2. Call Groq API
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0,
                max_tokens=1024,
                top_p=1,
                stream=False,
            )
            
            ai_reply = completion.choices[0].message.content
            
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
