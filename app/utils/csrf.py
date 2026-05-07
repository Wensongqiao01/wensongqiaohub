"""CSRF 保护 — double-submit cookie 模式"""

import secrets
from typing import Optional

from fastapi import Request, HTTPException
from starlette.datastructures import FormData


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def get_cookie_token(request: Request) -> Optional[str]:
    return request.cookies.get("csrftoken")


async def validate_csrf(request: Request) -> None:
    """依赖项：校验 CSRF token（用于管理 POST 路由）"""
    cookie_token = get_cookie_token(request)
    if not cookie_token:
        raise HTTPException(status_code=403, detail="CSRF token 缺失（cookie）")

    # 尝试从表单数据中获取 token
    body_token = None
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        body_token = form.get("csrftoken")
    elif request.headers.get("content-type", "") == "application/x-www-form-urlencoded":
        form = await request.form()
        body_token = form.get("csrftoken")
    else:
        body_token = request.headers.get("X-CSRFToken")

    if not body_token:
        raise HTTPException(status_code=403, detail="CSRF token 缺失（表单/header）")

    if not secrets.compare_digest(cookie_token, str(body_token)):
        raise HTTPException(status_code=403, detail="CSRF token 不匹配")
