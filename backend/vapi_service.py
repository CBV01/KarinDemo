import os
import httpx
import logging

logger = logging.getLogger("VapiService")

class VapiService:
    def __init__(self):
        self.api_key = os.getenv("VAPI_API_KEY")
        self.assistant_id = os.getenv("VAPI_ASSISTANT_ID")
        self.base_url = "https://api.vapi.ai"

    async def trigger_outbound_call(self, phone: str, lead_name: str, property_address: str):
        if not self.api_key:
            logger.info(f"[MOCK VAPI] Triggering call for {lead_name} at {phone}")
            return True
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "assistantId": self.assistant_id,
            "phoneNumberId": os.getenv("VAPI_PHONE_NUMBER_ID"), # optional if default set
            "customer": {
                "number": phone,
                "name": lead_name
            },
            "assistantOverrides": {
                "variableValues": {
                    "property_address": property_address,
                    "lead_name": lead_name
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.base_url}/call", json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error triggering Vapi call: {e}")
                return False
