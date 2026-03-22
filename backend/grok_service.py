import os
import httpx
from typing import List, Dict

class GrokService:
    def __init__(self, db_client):
        self.api_key = os.getenv("XAI_API_KEY")
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.db = db_client

    async def get_response(self, user_id: str, message: str) -> str:
        # 1. Fetch history from Turso
        history_sql = "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at ASC LIMIT 10"
        result = await self.db.execute(history_sql, (user_id,))
        
        messages = [{"role": "system", "content": "You are Karin's Real Estate AI Assistant. Help her manage leads, anniversaries, and campaigns. Keep it professional but friendly."}]
        
        for row in result.rows:
            messages.append({"role": row[0], "content": row[1]})
            
        messages.append({"role": "user", "content": message})

        # 2. Call xAI API
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "grok-beta",
                        "messages": messages,
                        "stream": False
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                ai_reply = data['choices'][0]['message']['content']
                
                # 3. Save to History
                await self.save_message(user_id, "user", message)
                await self.save_message(user_id, "assistant", ai_reply)
                
                return ai_reply
            except Exception as e:
                print(f"Grok API Error: {e}")
                return "I'm having trouble connecting to my brain (Grok) right now. Please try again later!"

    async def save_message(self, user_id: str, role: str, content: str):
        from uuid import uuid4
        sql = "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)"
        await self.db.execute(sql, (user_id, role, content))
