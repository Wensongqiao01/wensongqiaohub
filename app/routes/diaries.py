"""日记路由"""

from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import DIARY_PAGE_SIZE, SITE_TITLE
from app.database import get_db
from app.services import diary_service
from app.utils.csrf import get_cookie_token, validate_csrf
from app.utils.locals import require_local
from app.utils.markdown import render_markdown

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


def _context(request: Request):
    return {
        "request": request,
        "site_title": SITE_TITLE,
        "current_year": datetime.now().year,
        "csrftoken": get_cookie_token(request) or "",
        "is_local": request.client.host in ("127.0.0.1", "::1", "localhost")
        if request.client else False,
    }


# ==================== 公开路由 ====================


@router.get("/diaries", response_class=HTMLResponse)
async def diary_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
):
    """公开日记列表"""
    entries, total = diary_service.get_public_diaries(db, page, DIARY_PAGE_SIZE)
    total_pages = max(1, (total + DIARY_PAGE_SIZE - 1) // DIARY_PAGE_SIZE)

    context = _context(request)
    context.update({
        "active_page": "diaries",
        "entries": entries,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })
    return templates.TemplateResponse(request, "diaries/list.html", context)


@router.get("/diaries/{diary_id}", response_class=HTMLResponse)
async def diary_detail(
    request: Request,
    diary_id: int,
    db: Session = Depends(get_db),
):
    """日记详情"""
    diary = diary_service.get_diary_by_id(db, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记未找到")

    # 私密日记只允许本地访问
    is_local = request.client.host in ("127.0.0.1", "::1", "localhost") if request.client else False
    if not diary.is_public and not is_local:
        raise HTTPException(status_code=404, detail="日记未找到")

    prev_entry, next_entry = diary_service.get_adjacent_entries(db, diary_id, is_local)
    html_content = render_markdown(diary.content)

    context = _context(request)
    context.update({
        "active_page": "diaries",
        "diary": diary,
        "html_content": html_content,
        "prev_entry": prev_entry,
        "next_entry": next_entry,
    })
    return templates.TemplateResponse(request, "diaries/detail.html", context)


@router.post("/diaries/{diary_id}/like")
async def diary_like(
    diary_id: int,
    db: Session = Depends(get_db),
):
    """点赞日记（无需认证，返回 JSON）"""
    diary = diary_service.get_diary_by_id(db, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记未找到")

    new_count = diary_service.like_diary(db, diary)
    return JSONResponse({"likes_count": new_count})


# ==================== 管理路由（仅本地） ====================


@router.get("/manage/diaries", response_class=HTMLResponse)
async def manage_diary_list(
    request: Request,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理：所有日记列表"""
    entries = diary_service.get_all_diaries(db)

    context = _context(request)
    context.update({
        "active_page": "manage_diaries",
        "entries": entries,
    })
    return templates.TemplateResponse(request, "diaries/list.html", context)


@router.get("/manage/diaries/new", response_class=HTMLResponse)
async def manage_diary_new(
    request: Request,
    _=Depends(require_local),
):
    """管理：新建日记表单"""
    context = _context(request)
    context.update({
        "active_page": "manage_diaries",
        "diary": None,
    })
    return templates.TemplateResponse(request, "diaries/form.html", context)


@router.post("/manage/diaries")
async def manage_diary_create(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    is_public: bool = Form(False),
    mood: str = Form(""),
    tags: str = Form(""),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：创建日记"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")
    if not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    diary_service.create_diary(
        db,
        title=title.strip(),
        content=content.strip(),
        is_public=is_public,
        mood=mood.strip() or None,
        tags=tags.strip() or None,
    )
    return RedirectResponse(url="/manage/diaries", status_code=303)


@router.get("/manage/diaries/{diary_id}/edit", response_class=HTMLResponse)
async def manage_diary_edit(
    request: Request,
    diary_id: int,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理：编辑日记表单"""
    diary = diary_service.get_diary_by_id(db, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记未找到")

    context = _context(request)
    context.update({
        "active_page": "manage_diaries",
        "diary": diary,
    })
    return templates.TemplateResponse(request, "diaries/form.html", context)


@router.post("/manage/diaries/{diary_id}/edit")
async def manage_diary_update(
    request: Request,
    diary_id: int,
    title: str = Form(...),
    content: str = Form(...),
    is_public: bool = Form(False),
    mood: str = Form(""),
    tags: str = Form(""),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：更新日记"""
    diary = diary_service.get_diary_by_id(db, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记未找到")

    if not title.strip():
        raise HTTPException(status_code=400, detail="标题不能为空")

    diary_service.update_diary(
        db,
        diary,
        title=title.strip(),
        content=content.strip(),
        is_public=is_public,
        mood=mood.strip() or None,
        tags=tags.strip() or None,
    )
    return RedirectResponse(url="/manage/diaries", status_code=303)


@router.post("/manage/diaries/{diary_id}/delete")
async def manage_diary_delete(
    request: Request,
    diary_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：删除日记"""
    diary = diary_service.get_diary_by_id(db, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记未找到")

    diary_service.delete_diary(db, diary)
    return RedirectResponse(url="/manage/diaries", status_code=303)
