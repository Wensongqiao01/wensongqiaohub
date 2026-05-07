"""作品集路由"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import SITE_TITLE, SITE_AUTHOR, SITE_DESCRIPTION
from app.database import get_db
from app.models.setting import SiteSetting
from app.services import project_service
from app.utils.csrf import get_cookie_token, validate_csrf
from app.utils.locals import require_local

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()

DEFAULT_CATEGORIES = [
    {"key": "web", "name": "Web", "icon": "🌐"},
    {"key": "tool", "name": "工具", "icon": "🔧"},
    {"key": "design", "name": "设计", "icon": "🎨"},
    {"key": "ai", "name": "AI / ML", "icon": "🧠"},
    {"key": "other", "name": "其他", "icon": "📁"},
]


def _load_categories(db: Session) -> list[dict]:
    """从数据库加载作品分类配置"""
    row = db.query(SiteSetting).filter(SiteSetting.key == "project_categories").first()
    if row and row.value:
        try:
            return json.loads(row.value)
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_CATEGORIES


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


@router.get("/projects", response_class=HTMLResponse)
async def project_list(
    request: Request,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """作品集公开页面"""
    projects = project_service.get_projects(db, category=category)
    categories = _load_categories(db)
    category_dict = {c["key"]: c for c in categories}

    context = _context(request)
    context.update({
        "active_page": "projects",
        "projects": projects,
        "current_category": category or "",
        "categories": categories,
        "category_dict": category_dict,
    })
    return templates.TemplateResponse(request, "projects/list.html", context)


# ==================== 管理路由（仅本地） ====================


@router.get("/manage/projects", response_class=HTMLResponse)
async def manage_projects(
    request: Request,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理端作品列表（仅本地）"""
    projects = project_service.get_projects(db, published_only=False)
    categories = _load_categories(db)
    category_dict = {c["key"]: c for c in categories}

    context = _context(request)
    context.update({
        "active_page": "manage_projects",
        "projects": projects,
        "categories": categories,
        "category_dict": category_dict,
    })
    return templates.TemplateResponse(request, "projects/manage.html", context)


@router.get("/manage/projects/{project_id}/edit", response_class=HTMLResponse)
async def manage_project_edit_page(
    request: Request,
    project_id: int,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理端编辑作品页面（仅本地）"""
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="作品未找到")
    categories = _load_categories(db)
    category_dict = {c["key"]: c for c in categories}

    context = _context(request)
    context.update({
        "active_page": "manage_projects",
        "project": project,
        "categories": categories,
        "category_dict": category_dict,
    })
    return templates.TemplateResponse(request, "projects/edit.html", context)


@router.get("/manage/projects/{project_id}/data")
async def manage_project_data(
    request: Request,
    project_id: int,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """获取作品 JSON 数据（仅本地）"""
    from fastapi.responses import JSONResponse

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="作品未找到")

    return JSONResponse({
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "category": project.category,
        "tags": project.tags or "",
        "demo_url": project.demo_url or "",
        "source_url": project.source_url or "",
        "image_url": project.image_url or "",
        "order": project.order,
        "is_published": project.is_published,
    })


@router.post("/manage/projects/create")
async def manage_project_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("other"),
    tags: str = Form(""),
    demo_url: str = Form(""),
    source_url: str = Form(""),
    image_url: str = Form(""),
    order: int = Form(0),
    is_published: bool = Form(False),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """创建作品（仅本地）"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")

    project_service.create_project(
        db,
        title=title.strip(),
        description=description.strip(),
        category=category,
        tags=tags.strip(),
        demo_url=demo_url.strip() or None,
        source_url=source_url.strip() or None,
        image_url=image_url.strip() or None,
        order=order,
        is_published=is_published,
    )
    return RedirectResponse(url="/manage/projects", status_code=303)


@router.post("/manage/projects/{project_id}/edit")
async def manage_project_edit(
    request: Request,
    project_id: int,
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("other"),
    tags: str = Form(""),
    demo_url: str = Form(""),
    source_url: str = Form(""),
    image_url: str = Form(""),
    order: int = Form(0),
    is_published: bool = Form(False),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """编辑作品（仅本地）"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")

    project = project_service.update_project(
        db,
        project_id,
        title=title.strip(),
        description=description.strip(),
        category=category,
        tags=tags.strip(),
        demo_url=demo_url.strip() or None,
        source_url=source_url.strip() or None,
        image_url=image_url.strip() or None,
        order=order,
        is_published=is_published,
    )
    if not project:
        raise HTTPException(status_code=404, detail="作品未找到")
    return RedirectResponse(url="/manage/projects", status_code=303)


@router.post("/manage/projects/{project_id}/toggle-publish")
async def manage_project_toggle_publish(
    request: Request,
    project_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """切换发布状态（仅本地）"""
    from fastapi.responses import JSONResponse

    project = project_service.toggle_publish(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="作品未找到")
    return JSONResponse({"is_published": project.is_published})


@router.post("/manage/projects/{project_id}/delete")
async def manage_project_delete(
    request: Request,
    project_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """删除作品（仅本地）"""
    deleted = project_service.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="作品未找到")
    return RedirectResponse(url="/manage/projects", status_code=303)
