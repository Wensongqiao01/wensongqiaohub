"""站点设置路由"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import SITE_TITLE
from app.database import get_db
from app.models.setting import SiteSetting
from app.utils.csrf import get_cookie_token, validate_csrf
from app.utils.locals import require_local

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


def _load_settings(db: Session) -> dict:
    """从数据库加载所有站点设置"""
    rows = db.query(SiteSetting).all()
    return {r.key: r.value for r in rows}


def _context(request: Request):
    return {
        "request": request,
        "site_title": SITE_TITLE,
        "current_year": datetime.now().year,
        "csrftoken": get_cookie_token(request) or "",
        "is_local": request.client.host in ("127.0.0.1", "::1", "localhost")
        if request.client else False,
    }


@router.get("/manage/settings", response_class=HTMLResponse)
async def manage_settings(
    request: Request,
    saved: bool = False,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理：站点设置"""
    settings = _load_settings(db)

    # 解析分类 JSON 供前端编辑器使用
    project_categories_raw = settings.get("project_categories", "[]")
    try:
        project_categories_parsed = json.loads(project_categories_raw)
    except (json.JSONDecodeError, TypeError):
        project_categories_parsed = []

    # 解析多照片 JSON
    photo_urls_raw = settings.get("photo_urls", "[]")
    try:
        photo_urls = json.loads(photo_urls_raw)
    except (json.JSONDecodeError, TypeError):
        photo_urls = []

    context = _context(request)
    context.update({
        "active_page": "settings",
        "settings": settings,
        "project_categories_parsed": project_categories_parsed,
        "photo_urls": photo_urls,
        "show_saved": saved,
    })
    return templates.TemplateResponse(request, "manage/settings.html", context)


@router.post("/manage/settings")
async def manage_settings_save(
    request: Request,
    site_author: str = Form(""),
    photo_url: str = Form(""),
    about_me: str = Form(""),
    contact_email: str = Form(""),
    contact_github: str = Form(""),
    project_categories: str = Form(""),
    photo_urls: str = Form("[]"),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：保存站点设置"""
    if not site_author.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")

    updates = {
        "site_author": site_author.strip(),
        "photo_url": photo_url.strip(),
        "about_me": about_me.strip(),
        "contact_email": contact_email.strip(),
        "contact_github": contact_github.strip(),
        "project_categories": project_categories,
        "photo_urls": photo_urls,
    }
    for key, value in updates.items():
        setting = db.query(SiteSetting).filter(SiteSetting.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(SiteSetting(key=key, value=value))
    db.commit()

    return RedirectResponse(url="/manage/settings?saved=1", status_code=303)
