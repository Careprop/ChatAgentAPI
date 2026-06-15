import hmac

from fastapi import Header, HTTPException

from app.config.settings import settings


async def verify_api_key(x_api_key: str = Header(...)):
    if not hmac.compare_digest(x_api_key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")
