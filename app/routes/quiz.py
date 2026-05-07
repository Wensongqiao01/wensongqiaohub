"""测验路由"""

import json
import logging
import urllib.parse
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import SITE_TITLE, UNSPLASH_ACCESS_KEY, PEXELS_API_KEY
from app.database import get_db
from app.models.quiz import QuizQuestion
from app.services import quiz_service
from app.services.pexels_service import (
    fetch_option_images as pexels_fetch_option_images,
    fetch_question_image as pexels_fetch_question_image,
    fetch_image_candidates as pexels_fetch_image_candidates,
    fetch_option_candidates as pexels_fetch_option_candidates,
)
from app.services.unsplash_service import (
    fetch_option_images as unsplash_fetch_option_images,
    fetch_question_image as unsplash_fetch_question_image,
    fetch_image_candidates as unsplash_fetch_image_candidates,
    fetch_option_candidates as unsplash_fetch_option_candidates,
)
from app.utils.csrf import get_cookie_token, validate_csrf
from app.utils.locals import require_local

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()
logger = logging.getLogger(__name__)


def _validate_image_url(url: str) -> bool:
    """验证图片 URL 格式是否合法"""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


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


@router.get("/quiz", response_class=HTMLResponse)
async def quiz_play(
    request: Request,
    db: Session = Depends(get_db),
):
    """测验游戏页面"""
    questions = quiz_service.get_shuffled_questions(db)

    # 构建前端数据（不包含正确答案）
    quiz_data = [
        {
            "id": q.id,
            "question": q.question,
            "options": json.loads(q.options),
            "option_images": json.loads(q.option_images) if q.option_images else None,
            "image_url": q.image_url,
        }
        for q in questions
    ]

    context = _context(request)
    context.update({
        "active_page": "quiz",
        "quiz_data": json.dumps(quiz_data, ensure_ascii=False).replace("</", "\\u003C/"),
        "question_count": len(questions),
    })
    return templates.TemplateResponse(request, "quiz/play.html", context)


@router.post("/quiz/submit")
async def quiz_submit(request: Request, db: Session = Depends(get_db)):
    """提交测验答案"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "无效的 JSON 格式"},
        )

    answers = body.get("answers", [])
    player_name = body.get("player_name")

    if not answers:
        return JSONResponse(
            status_code=400,
            content={"error": "请至少回答一道题"},
        )

    result = quiz_service.submit_answers(db, answers, player_name)
    return result


@router.get("/quiz/results", response_class=HTMLResponse)
async def quiz_results(
    request: Request,
    db: Session = Depends(get_db),
):
    """测验结果历史"""
    attempts = quiz_service.get_attempts(db)

    context = _context(request)
    context.update({
        "active_page": "quiz",
        "attempts": attempts,
    })
    return templates.TemplateResponse(request, "quiz/results.html", context)


# ==================== 管理路由（仅本地） ====================


@router.get("/manage/quiz", response_class=HTMLResponse)
async def manage_quiz(
    request: Request,
    _=Depends(require_local),
    db: Session = Depends(get_db),
):
    """管理：题目列表"""
    questions = quiz_service.get_all_questions(db)

    # 预解析 options JSON 字段
    parsed = []
    for q in questions:
        parsed.append({
            "id": q.id,
            "question": q.question,
            "options": json.loads(q.options),
            "correct_index": q.correct_index,
            "explanation": q.explanation,
            "order": q.order,
            "is_published": q.is_published,
            "image_url": q.image_url,
            "option_images": json.loads(q.option_images) if q.option_images else None,
        })

    context = _context(request)
    context.update({
        "active_page": "manage_quiz",
        "questions": parsed,
    })
    return templates.TemplateResponse(request, "quiz/manage.html", context)


@router.post("/manage/quiz/questions")
async def manage_quiz_create(
    request: Request,
    question: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_index: int = Form(...),
    explanation: str = Form(""),
    order: int = Form(0),
    is_published: bool = Form(False),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：创建题目"""
    if not question.strip():
        raise HTTPException(status_code=400, detail="题目不能为空")

    options = [option_a, option_b, option_c, option_d]
    if not all(o.strip() for o in options):
        raise HTTPException(status_code=400, detail="所有选项不能为空")
    if correct_index not in range(4):
        raise HTTPException(status_code=400, detail="正确答案索引无效")

    q = quiz_service.create_question(
        db,
        question=question.strip(),
        options=options,
        correct_index=correct_index,
        explanation=explanation.strip() or None,
        order=order,
        is_published=is_published,
    )

    # 自动获取选项配图（优先 Pexels，降级 Unsplash）
    try:
        option_images: list[str | None] = [None] * 4
        if PEXELS_API_KEY:
            pexels_images = await pexels_fetch_option_images(options)
            if any(pexels_images):
                option_images = pexels_images
        if not any(option_images) and UNSPLASH_ACCESS_KEY:
            unsplash_images = await unsplash_fetch_option_images(options)
            if any(unsplash_images):
                option_images = unsplash_images
        if any(option_images):
            quiz_service.update_option_images(db, q, option_images)
    except Exception as e:
        logger.warning("自动获取选项配图失败: %s", e)

    return RedirectResponse(url="/manage/quiz", status_code=303)


@router.post("/manage/quiz/questions/{question_id}/edit")
async def manage_quiz_update(
    request: Request,
    question_id: int,
    question: str = Form(...),
    option_a: str = Form(...),
    option_b: str = Form(...),
    option_c: str = Form(...),
    option_d: str = Form(...),
    correct_index: int = Form(...),
    explanation: str = Form(""),
    order: int = Form(0),
    is_published: bool = Form(False),
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：更新题目"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()

    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    if not question.strip():
        raise HTTPException(status_code=400, detail="题目不能为空")

    options = [option_a, option_b, option_c, option_d]
    if not all(o.strip() for o in options):
        raise HTTPException(status_code=400, detail="所有选项不能为空")

    quiz_service.update_question(
        db,
        question_obj,
        question=question.strip(),
        options=options,
        correct_index=correct_index,
        explanation=explanation.strip() or None,
        order=order,
        is_published=is_published,
    )
    return RedirectResponse(url="/manage/quiz", status_code=303)


@router.post("/manage/quiz/questions/{question_id}/delete")
async def manage_quiz_delete(
    request: Request,
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """管理：删除题目"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()

    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    quiz_service.delete_question(db, question_obj)
    return RedirectResponse(url="/manage/quiz", status_code=303)


@router.post("/manage/quiz/questions/{question_id}/toggle-publish")
async def manage_quiz_toggle_publish(
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """切换题目的发布状态"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    new_state = quiz_service.toggle_publish(db, question_obj)
    return JSONResponse({"is_published": new_state})


@router.post("/manage/quiz/questions/{question_id}/fetch-image")
async def manage_quiz_fetch_image(
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """根据题目内容获取配图（优先 Pexels，降级 Unsplash）"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    image_url: str | None = None
    source = ""

    if PEXELS_API_KEY:
        try:
            image_url = await pexels_fetch_question_image(question_obj.question)
            if image_url:
                source = "Pexels"
        except Exception as e:
            logger.warning("Pexels 获取配图失败: %s", e)

    if not image_url and UNSPLASH_ACCESS_KEY:
        try:
            image_url = await unsplash_fetch_question_image(question_obj.question)
            if image_url:
                source = "Unsplash"
        except Exception as e:
            logger.warning("Unsplash 获取配图失败: %s", e)

    if not image_url:
        return JSONResponse(
            status_code=400,
            content={"error": "未找到相关配图，请检查题目内容或 API 配置"},
        )

    quiz_service.update_image(db, question_obj, image_url)
    return JSONResponse({"image_url": image_url, "source": source})


@router.post("/manage/quiz/questions/{question_id}/fetch-option-images")
async def manage_quiz_fetch_option_images(
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """根据选项内容批量获取配图（优先 Pexels，降级 Unsplash）"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    options = json.loads(question_obj.options)
    option_images: list[str | None] = [None] * 4

    if PEXELS_API_KEY:
        try:
            pexels_images = await pexels_fetch_option_images(options)
            if any(pexels_images):
                option_images = pexels_images
        except Exception as e:
            logger.warning("Pexels 获取选项配图失败: %s", e)

    if not any(option_images) and UNSPLASH_ACCESS_KEY:
        try:
            unsplash_images = await unsplash_fetch_option_images(options)
            if any(unsplash_images):
                option_images = unsplash_images
        except Exception as e:
            logger.warning("Unsplash 获取选项配图失败: %s", e)

    if not any(option_images):
        return JSONResponse(
            status_code=400,
            content={"error": "未找到相关配图，请检查选项内容或 API 配置"},
        )

    quiz_service.update_option_images(db, question_obj, option_images)
    return JSONResponse({"option_images": option_images})


# ==================== 候选图片选择器端点 ====================


@router.post("/manage/quiz/questions/{question_id}/fetch-image-candidates")
async def manage_quiz_fetch_image_candidates(
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """获取题目配图候选列表（优先 Pexels，降级 Unsplash）"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    candidates = []
    if PEXELS_API_KEY:
        try:
            candidates = await pexels_fetch_image_candidates(question_obj.question)
        except Exception as e:
            logger.warning("Pexels 获取候选配图失败: %s", e)

    if not candidates and UNSPLASH_ACCESS_KEY:
        try:
            candidates = await unsplash_fetch_image_candidates(question_obj.question)
        except Exception as e:
            logger.warning("Unsplash 获取候选配图失败: %s", e)

    if not candidates:
        return JSONResponse(
            status_code=400,
            content={"error": "未找到候选配图，请检查 API 配置"},
        )

    return JSONResponse(content=[
        {"url": c.url, "thumb_url": c.thumb_url, "author": c.author, "likes": c.likes}
        for c in candidates
    ])


@router.post("/manage/quiz/questions/{question_id}/select-image")
async def manage_quiz_select_image(
    question_id: int,
    request: Request,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """保存用户选中的题目配图"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效的 JSON 格式"})

    image_url = body.get("image_url")
    if not image_url:
        return JSONResponse(status_code=400, content={"error": "image_url 不能为空"})
    if not _validate_image_url(image_url):
        return JSONResponse(status_code=400, content={"error": "无效的图片 URL"})

    quiz_service.update_image(db, question_obj, image_url)
    return JSONResponse({"image_url": image_url})


@router.post("/manage/quiz/questions/{question_id}/fetch-option-candidates")
async def manage_quiz_fetch_option_candidates(
    question_id: int,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """获取每个选项的候选配图列表（优先 Pexels，降级 Unsplash）"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    options = json.loads(question_obj.options)
    candidates_per_option = []

    if PEXELS_API_KEY:
        try:
            candidates_per_option = await pexels_fetch_option_candidates(options)
        except Exception as e:
            logger.warning("Pexels 获取选项候选配图失败: %s", e)

    if not candidates_per_option or not any(candidates_per_option):
        if UNSPLASH_ACCESS_KEY:
            try:
                candidates_per_option = await unsplash_fetch_option_candidates(options)
            except Exception as e:
                logger.warning("Unsplash 获取选项候选配图失败: %s", e)

    if not candidates_per_option or not any(candidates_per_option):
        return JSONResponse(
            status_code=400,
            content={"error": "未找到候选配图，请检查 API 配置"},
        )

    result = []
    for opt_candidates in candidates_per_option:
        result.append([
            {"url": c.url, "thumb_url": c.thumb_url, "author": c.author, "likes": c.likes}
            for c in opt_candidates
        ])
    return JSONResponse(content=result)


@router.post("/manage/quiz/questions/{question_id}/select-option-images")
async def manage_quiz_select_option_images(
    question_id: int,
    request: Request,
    _=Depends(require_local),
    _csrf=Depends(validate_csrf),
    db: Session = Depends(get_db),
):
    """保存用户选中的选项配图"""
    question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == question_id).first()
    if not question_obj:
        raise HTTPException(status_code=404, detail="题目未找到")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效的 JSON 格式"})

    option_images = body.get("option_images", [])
    if not option_images or len(option_images) != 4:
        return JSONResponse(status_code=400, content={"error": "需要提供 4 个选项图片 URL"})
    for url in option_images:
        if url and not _validate_image_url(url):
            return JSONResponse(status_code=400, content={"error": "包含无效的图片 URL"})

    quiz_service.update_option_images(db, question_obj, option_images)
    return JSONResponse({"option_images": option_images})
