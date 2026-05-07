"""作品集业务逻辑"""

from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import asc

from app.models.project import Project


def get_projects(
    db: Session,
    category: str | None = None,
    published_only: bool = True,
) -> list[Project]:
    """获取作品列表，按 order 升序"""
    query = db.query(Project)
    if published_only:
        query = query.filter(Project.is_published.is_(True))
    if category:
        query = query.filter(Project.category == category)
    return query.order_by(asc(Project.order)).all()


def get_project(db: Session, project_id: int) -> Project | None:
    """获取单个作品"""
    return db.query(Project).filter(Project.id == project_id).first()


def get_categories(db: Session) -> list[str]:
    """获取所有使用的分类"""
    results = db.query(Project.category).distinct().all()
    return [r[0] for r in results if r[0]]


def create_project(
    db: Session,
    title: str,
    description: str,
    category: str = "other",
    tags: str = "",
    demo_url: str | None = None,
    source_url: str | None = None,
    image_url: str | None = None,
    order: int = 0,
    is_published: bool = False,
) -> Project:
    """创建新作品"""
    proj = Project(
        title=title.strip(),
        description=description.strip(),
        category=category,
        tags=tags,
        demo_url=demo_url,
        source_url=source_url,
        image_url=image_url,
        order=order,
        is_published=is_published,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


def update_project(
    db: Session,
    project_id: int,
    **kwargs,
) -> Project | None:
    """更新作品"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if proj:
        for key, value in kwargs.items():
            if hasattr(proj, key):
                setattr(proj, key, value)
        proj.updated_at = datetime.now()
        db.commit()
        db.refresh(proj)
    return proj


def toggle_publish(db: Session, project_id: int) -> Project | None:
    """切换发布状态"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if proj:
        proj.is_published = not proj.is_published
        proj.updated_at = datetime.now()
        db.commit()
        db.refresh(proj)
    return proj


def delete_project(db: Session, project_id: int) -> bool:
    """删除作品"""
    proj = db.query(Project).filter(Project.id == project_id).first()
    if proj:
        db.delete(proj)
        db.commit()
        return True
    return False
