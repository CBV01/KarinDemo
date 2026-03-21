import asyncio
from libsql_client import create_client_sync
import os
from dotenv import load_dotenv
load_dotenv()
from google_auth import GoogleAuthService

async def main():
    db = create_client_sync(url=os.getenv('TURSO_DB_URL'), auth_token=os.getenv('TURSO_DB_TOKEN'))
    auth_service = GoogleAuthService(db)
    try:
        await auth_service.save_token("1234")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
