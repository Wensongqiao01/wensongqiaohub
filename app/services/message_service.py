"""留言板业务逻辑"""

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.message import Message


def get_messages(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Message], int]:
    """获取留言列表，置顶在前，按时间倒序"""
    total = db.query(Message).count()
    pinned = (
        db.query(Message)
        .filter(Message.is_pinned.is_(True))
        .order_by(desc(Message.created_at))
        .all()
    )
    unpinned = (
        db.query(Message)
        .filter(Message.is_pinned.is_(False))
        .order_by(desc(Message.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    messages = pinned + unpinned
    return messages, total


def create_message(
    db: Session,
    nickname: str,
    content: str,
) -> Message:
    """创建新留言"""
    msg = Message(nickname=nickname.strip()[:50], content=content.strip()[:2000])
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def toggle_pin(db: Session, message_id: int) -> Message | None:
    """切换置顶状态"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg:
        msg.is_pinned = not msg.is_pinned
        db.commit()
        db.refresh(msg)
    return msg


def delete_message(db: Session, message_id: int) -> bool:
    """删除留言"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg:
        db.delete(msg)
        db.commit()
        return True
    return False
