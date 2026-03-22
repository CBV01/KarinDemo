import os
import json
import urllib.request
import ssl
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

        # 2. Call xAI API using urllib (more robust for Hugging Face DNS)
        if not self.api_key:
            return "❌ Grok brain error: XAI_API_KEY is missing in HF Secrets!"

        payload = json.dumps({
            "model": "grok-4-1-fast",
            "messages": messages,
            "stream": False,
            "temperature": 0
        }).encode('utf-8')

        try:
            req = urllib.request.Request(
                self.base_url, 
                data=payload, 
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            # Using a context with custom timeouts
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                ai_reply = res_data['choices'][0]['message']['content']
                
                # 3. Save to History
                await self.save_message(user_id, "user", message)
                await self.save_message(user_id, "assistant", ai_reply)
                
                return ai_reply

        except Exception as e:
            print(f"Grok API Error (urllib): {e}")
            
            # Fallback to grok-beta if grok-4-1-fast fails
            try:
                print("Attempting fallback to 'grok-beta'...")
                payload_fallback = json.dumps({
                    "model": "grok-beta",
                    "messages": messages,
                    "stream": False,
                    "temperature": 0
                }).encode('utf-8')
                
                req_fallback = urllib.request.Request(
                    self.base_url, 
                    data=payload_fallback, 
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req_fallback, timeout=30) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    ai_reply = res_data['choices'][0]['message']['content']
                    await self.save_message(user_id, "user", message)
                    await self.save_message(user_id, "assistant", ai_reply)
                    return ai_reply
            except Exception as e2:
                print(f"Grok Fallback also failed: {e2}")
                return f"I'm having trouble connecting to my brain (Grok) right now. Error: {str(e2)}"
        
        return "I'm thinking... but nothing came out. Try asking me again!"

    async def save_message(self, user_id: str, role: str, content: str):
        from uuid import uuid4
        sql = "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)"
        await self.db.execute(sql, (user_id, role, content))
