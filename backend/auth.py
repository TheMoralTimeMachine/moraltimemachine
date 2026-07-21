from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException

from backend import db

async def require_participant(x_participant_key: str = Header(default="")) -> str:
    key = x_participant_key.strip()
    if not key or not db.participant_exists(key):
        raise HTTPException(401, "invalid or missing participant key")
    return key

async def require_admin(x_admin_key: str = Header(default="")) -> None:
    configured = os.getenv("MTM_ADMIN_KEY", "")
    if not configured:
        raise HTTPException(403, "admin access is not configured")
    if not secrets.compare_digest(x_admin_key.strip(), configured):
        raise HTTPException(401, "invalid admin key")
