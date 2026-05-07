"""数据库引擎和会话管理"""

import json

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def _add_column_if_not_exists(table: str, column: str, col_type: str) -> None:
    """添加数据库列（如不存在）"""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table)]
    if column not in columns:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()


def _seed_settings() -> None:
    """初始化站点设置默认值"""
    from app.models.setting import SiteSetting

    defaults = {
        "site_author": "你的名字",
        "photo_url": "",
        "about_me": "这里是你的一段简短自我介绍。可以写写你的职业、爱好、或者任何你想分享的事情。",
        "contact_email": "",
        "contact_github": "",
        "project_categories": json.dumps([
            {"key": "web", "name": "Web", "icon": "🌐"},
            {"key": "tool", "name": "工具", "icon": "🔧"},
            {"key": "design", "name": "设计", "icon": "🎨"},
            {"key": "ai", "name": "AI / ML", "icon": "🧠"},
            {"key": "other", "name": "其他", "icon": "📁"},
        ], ensure_ascii=False),
    }
    db = SessionLocal()
    try:
        for key, value in defaults.items():
            existing = db.query(SiteSetting).filter(SiteSetting.key == key).first()
            if not existing:
                db.add(SiteSetting(key=key, value=value))
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    """初始化数据库，创建所有表并执行迁移"""
    import app.models.diary  # noqa: F401
    import app.models.message  # noqa: F401
    import app.models.project  # noqa: F401
    import app.models.quiz  # noqa: F401
    import app.models.setting  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 迁移：新增列
    _add_column_if_not_exists("diaries", "likes_count", "INTEGER DEFAULT 0")
    _add_column_if_not_exists("quiz_questions", "is_published", "BOOLEAN DEFAULT 0")
    _add_column_if_not_exists("quiz_questions", "image_url", "VARCHAR(500)")
    _add_column_if_not_exists("quiz_questions", "option_images", "TEXT")

    # 种子数据
    _seed_settings()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
