"""留言板路由"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import SITE_TITLE, SITE_AUTHOR, SITE_DESCRIPTION
from app.database import get_db
from app.services import message_service
from app.utils.csrf import get_cookie_token, validate_csrf
from app.utils.locals import require_local

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


def _context(request: Request):
    return {
        "request": request,
        "site_title": SITE_TITLE,
        "site_author": SITE_AUTHOR,
        "site_description": SITE_DESCRIPTION,
        "current_year": datetime.now().year,
        "csrftoken": get_cookie_token(request) or "",
        "is_local": request.client.host in ("127.0.0.1", "::1", "localhost")
        if request.client else False,
    }


# ==================== 公开路由 ====================


@router.get("/messages", response_class=HTMLResponse)
async def message_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
):
    """留言板公开页面"""
    messages, total = message_service.get_messages(db, page=page)
    page_size = 20
    total_pages = max(1, (total + page_size - 1) // page_size)

    context = _context(request)
    context.update({
        "active_page": "messages",
        "messages": messages,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })
    return templates.TemplateResponse(request, "messages/list.html", context)


@router.post("/messages")
async def message_create(
    request: Request,
    nickname: str = Form(...),
    content: str = Form(...),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """提交新留言"""
    if not nickname.strip() or not content.strip():
        raise HTTPException(status_code=400, detail="昵称和内容不能为空")

    message_service.create_message(
        db,
        nickname=nickname.strip()[:50],
        content=content.strip()[:2000],
    )
    return RedirectResponse(url="/messages", status_code=303)


# ==================== 管理路由（仅本地） ====================


@router.get("/manage/messages", response_class=HTMLResponse)
async def manage_messages(
    request: Request,
    page: int = 1,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理端留言列表（仅本地）"""
    messages, total = message_service.get_messages(db, page=page, page_size=20)
    page_size = 20
    total_pages = max(1, (total + page_size - 1) // page_size)

    context = _context(request)
    context.update({
        "active_page": "manage_messages",
        "messages": messages,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })
    return templates.TemplateResponse(request, "messages/manage.html", context)


@router.post("/manage/messages/{message_id}/toggle-pin")
async def message_toggle_pin(
    request: Request,
    message_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """切换置顶状态（仅本地）"""
    msg = message_service.toggle_pin(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="留言未找到")
    return RedirectResponse(url="/manage/messages", status_code=303)


@router.post("/manage/messages/{message_id}/delete")
async def message_delete(
    request: Request,
    message_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """删除留言（仅本地）"""
    deleted = message_service.delete_message(db, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="留言未找到")
    return RedirectResponse(url="/manage/messages", status_code=303)
