"""FastAPI 应用工厂"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import SITE_TITLE, DEBUG
from app.database import init_db
from app.utils.csrf import generate_token


class CSRFMiddleware(BaseHTTPMiddleware):
    """为所有响应设置 CSRF cookie（如未设置）"""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if "csrftoken" not in request.cookies:
            response.set_cookie(
                key="csrftoken",
                value=generate_token(),
                httponly=False,
                samesite="lax",
                secure=not DEBUG,
            )
        return response


# 创建应用
app = FastAPI(title=SITE_TITLE)

# 中间件
app.add_middleware(CSRFMiddleware)

# 静态文件
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 启动事件
@app.on_event("startup")
def on_startup():
    init_db()

# 注册路由
from app.routes import pages, diaries, quiz, settings, messages, projects  # noqa: E402
app.include_router(pages.router)
app.include_router(diaries.router)
app.include_router(quiz.router)
app.include_router(settings.router)
app.include_router(messages.router)
app.include_router(projects.router)
