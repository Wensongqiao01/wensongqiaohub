"""页面路由"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import SITE_TITLE, SITE_AUTHOR, SITE_DESCRIPTION
from app.database import get_db
from app.models.diary import Diary
from app.models.setting import SiteSetting
from app.utils.csrf import get_cookie_token

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 注册自定义过滤器
def json_loads(value: str) -> list:
    """加载 JSON 字符串为 Python 对象"""
    return json.loads(value) if value else []

templates.env.filters["json_loads"] = json_loads

router = APIRouter()


def _load_setting(db: Session, key: str, default: str = "") -> str:
    """从数据库加载单个站点设置"""
    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    return row.value if row else default


def _common_context(request: Request):
    """共享模板上下文"""
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


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db=Depends(get_db)):
    """首页"""
    from app.services.diary_service import get_public_diaries
    from app.services.message_service import get_messages
    from app.services.quiz_service import get_all_questions, get_attempts
    from app.services.project_service import get_projects

    entries, _ = get_public_diaries(db, page=1, page_size=3)
    questions = get_all_questions(db)
    attempts = get_attempts(db, limit=1)
    best_score = round((attempts[0].score / attempts[0].total) * 100) if attempts and attempts[0].total > 0 else None
    diary_count = db.query(Diary).filter(Diary.is_public == True).count()
    project_count = len(get_projects(db, published_only=True))
    recent_messages, _ = get_messages(db, page=1, page_size=10)

    # 加载可编辑的站点设置
    site_author = _load_setting(db, "site_author", SITE_AUTHOR)
    photo_url = _load_setting(db, "photo_url", "")
    about_me = _load_setting(db, "about_me", "")

    # 加载多照片
    photo_urls_raw = _load_setting(db, "photo_urls", "[]")
    try:
        photo_urls = json.loads(photo_urls_raw)
    except (json.JSONDecodeError, TypeError):
        photo_urls = []
    if photo_url and photo_url not in photo_urls:
        photo_urls.insert(0, photo_url)

    context = _common_context(request)
    context.update({
        "active_page": "home",
        "site_author": site_author,
        "photo_url": photo_url,
        "photo_urls": photo_urls,
        "about_me": about_me,
        "latest_diaries": entries,
        "quiz_count": len(questions),
        "quiz_best": best_score,
        "diary_count": diary_count,
        "project_count": project_count,
        "recent_messages": recent_messages,
    })
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request, db=Depends(get_db)):
    """关于页面"""
    about_me = _load_setting(db, "about_me", "")
    contact_email = _load_setting(db, "contact_email", "")
    contact_github = _load_setting(db, "contact_github", "")

    context = _common_context(request)
    context.update({
        "active_page": "about",
        "about_me": about_me,
        "contact_email": contact_email,
        "contact_github": contact_github,
    })
    return templates.TemplateResponse(request, "about.html", context)


@router.get("/404", response_class=HTMLResponse)
async def custom_404(request: Request):
    """404 页面"""
    context = _common_context(request)
    return templates.TemplateResponse(request, "404.html", context)
