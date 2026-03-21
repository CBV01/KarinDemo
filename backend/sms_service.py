import os
import logging
from twilio.rest import Client as TwilioClient

logger = logging.getLogger("SmsService")

class SmsService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if self.account_sid and self.auth_token:
            self.client = TwilioClient(self.account_sid, self.auth_token)
        else:
            self.client = None
            logger.warning("Twilio credentials not set. SMS sending will be mocked.")

    async def send_sms(self, to_number: str, message: str):
        if not self.client:
            logger.info(f"[MOCK SMS] To: {to_number} | Msg: {message}")
            return True
            
        try:
            self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            return True
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
