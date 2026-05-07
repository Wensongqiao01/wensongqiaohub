"""本地访问检测"""

import os

from fastapi import Request, HTTPException


async def require_local(request: Request) -> bool:
    """FastAPI 依赖：仅允许本地访问"""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        if os.getenv("DEV_ALLOW_REMOTE") != "1":
            raise HTTPException(status_code=403, detail="仅允许本地访问")
    return True
