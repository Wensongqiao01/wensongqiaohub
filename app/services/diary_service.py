"""日记业务逻辑"""

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.diary import Diary


def get_public_diaries(
    db: Session, page: int = 1, page_size: int = 10
) -> tuple[list[Diary], int]:
    """获取公开日记列表（分页）"""
    query = db.query(Diary).filter(Diary.is_public == True).order_by(desc(Diary.created_at))
    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()
    return entries, total


def get_all_diaries(db: Session) -> list[Diary]:
    """获取所有日记（管理用）"""
    return db.query(Diary).order_by(desc(Diary.created_at)).all()


def get_diary_by_id(db: Session, diary_id: int) -> Diary | None:
    """根据 ID 获取日记"""
    return db.query(Diary).filter(Diary.id == diary_id).first()


def get_adjacent_entries(
    db: Session, diary_id: int, is_local: bool = False
) -> tuple[Diary | None, Diary | None]:
    """获取上一篇和下一篇日记"""
    query = db.query(Diary)
    if not is_local:
        query = query.filter(Diary.is_public == True)

    prev_entry = (
        query.filter(Diary.id < diary_id)
        .order_by(desc(Diary.id))
        .first()
    )
    next_entry = (
        query.filter(Diary.id > diary_id)
        .order_by(Diary.id)
        .first()
    )
    return prev_entry, next_entry


def create_diary(
    db: Session,
    title: str,
    content: str,
    is_public: bool = False,
    mood: str | None = None,
    tags: str | None = None,
) -> Diary:
    """创建日记"""
    diary = Diary(
        title=title,
        content=content,
        is_public=is_public,
        mood=mood,
        tags=tags,
    )
    db.add(diary)
    db.commit()
    db.refresh(diary)
    return diary


def update_diary(
    db: Session,
    diary: Diary,
    title: str,
    content: str,
    is_public: bool,
    mood: str | None = None,
    tags: str | None = None,
) -> Diary:
    """更新日记"""
    diary.title = title
    diary.content = content
    diary.is_public = is_public
    diary.mood = mood
    diary.tags = tags
    db.commit()
    db.refresh(diary)
    return diary


def like_diary(db: Session, diary: Diary) -> int:
    """点赞日记，返回新的点赞数"""
    diary.likes_count = (diary.likes_count or 0) + 1
    db.commit()
    db.refresh(diary)
    return diary.likes_count


def delete_diary(db: Session, diary: Diary) -> None:
    """删除日记"""
    db.delete(diary)
    db.commit()
