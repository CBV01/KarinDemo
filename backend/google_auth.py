import os
import json
from typing import List, Optional
from google_auth_oauthlib.flow import Flow # type: ignore
from googleapiclient.discovery import build # type: ignore
from google.oauth2.credentials import Credentials # type: ignore
from google.auth.transport.requests import Request # type: ignore
from libsql_client import Client # type: ignore

class GoogleAuthService:
    def __init__(self, db: Client):
        self.db = db
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar'
        ]

    def get_auth_url(self):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        # Use a deterministic, high-entropy verifier for our stateless environment
        # This fixes the 'Missing code verifier' error without needing a session store
        cid = str(self.client_id or "default_id")
        csec = str(self.client_secret or "default_sec")
        verifier = f"HandshakeSecret_{cid[:10]}_{csec[:10]}" # type: ignore
        flow.code_verifier = verifier
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return auth_url

    async def save_token(self, code: str):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        # Use the same deterministic verifier to complete the handshake
        cid = str(self.client_id or "default_id")
        csec = str(self.client_secret or "default_sec")
        verifier = f"HandshakeSecret_{cid[:10]}_{csec[:10]}" # type: ignore
        flow.code_verifier = verifier
        try:
            flow.fetch_token(code=code)
        except Exception as e:
            print(f"Token Exchange Error: {e}")
            raise Exception(f"Failed to trade authorization code for tokens. Original error: {str(e)}")
            
        creds = flow.credentials

        # Save to DB
        sql = """
            INSERT INTO user_tokens (service, access_token, refresh_token, token_uri, client_id, client_secret, scopes, expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(service) DO UPDATE SET
                access_token=excluded.access_token,
                refresh_token=excluded.refresh_token,
                expiry=excluded.expiry
        """
        params = [
            'google',
            creds.token,
            creds.refresh_token,
            creds.token_uri,
            creds.client_id,
            creds.client_secret,
            ','.join(creds.scopes) if creds.scopes else '',
            creds.expiry.isoformat() if creds.expiry else None
        ]
        await self.db.execute(sql, params)
        return "Tokens saved successfully"

    async def create_anniversary_event(self, client_name: str, property_address: str, purchase_date: str):
        """
        Creates a calendar event for a property anniversary.
        """
        creds = await self.get_creds()
        if not creds:
            print("❌ Google Calendar not connected. Cannot create event.")
            return False

        try:
            service = build('calendar', 'v3', credentials=creds)
            
            # Purchase date is YYYY-MM-DD. Anniversary is every year.
            # We'll create a recurring yearly event.
            event = {
                'summary': f"🏠 Anniversary: {client_name} ({property_address})",
                'location': property_address,
                'description': f"Anniversary of property purchase for {client_name}.",
                'start': {
                    'date': purchase_date,
                    'timeZone': 'Pacific/Auckland',
                },
                'end': {
                    'date': purchase_date,
                    'timeZone': 'Pacific/Auckland',
                },
                'recurrence': [
                    'RRULE:FREQ=YEARLY'
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            event = service.events().insert(calendarId='primary', body=event).execute()
            print(f"✅ Calendar event created: {event.get('htmlLink')}")
            return True
        except Exception as e:
            print(f"❌ Error creating calendar event: {e}")
            return False

    async def get_creds(self):
        result = await self.db.execute("SELECT * FROM user_tokens WHERE service = 'google'")
        if not result.rows:
            return None
        
        row = dict(zip(result.columns, result.rows[0]))
        creds = Credentials(
            token=row['access_token'],
            refresh_token=row['refresh_token'],
            token_uri=row['token_uri'],
            client_id=row['client_id'],
            client_secret=row['client_secret'],
            scopes=row['scopes'].split(',')
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update DB with new access token
            await self.db.execute(
                "UPDATE user_tokens SET access_token = ?, expiry = ? WHERE service = 'google'",
                [creds.token, creds.expiry.isoformat() if creds.expiry else None]
            )
        
        return creds

    async def send_email(self, recipient: str, subject: str, body: str):
        creds = await self.get_creds()
        if not creds:
            raise Exception("Google Account not connected")
        
        service = build('gmail', 'v1', credentials=creds)
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return True
