"""测验业务逻辑"""

import json
import random

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.quiz import QuizQuestion, QuizAttempt


def get_all_questions(db: Session) -> list[QuizQuestion]:
    """获取所有题目，按 order 排序"""
    return db.query(QuizQuestion).order_by(QuizQuestion.order).all()


def get_published_questions(db: Session) -> list[QuizQuestion]:
    """获取已发布的题目，按 order 排序"""
    return (
        db.query(QuizQuestion)
        .filter(QuizQuestion.is_published == True)
        .order_by(QuizQuestion.order)
        .all()
    )


def get_shuffled_questions(db: Session) -> list[QuizQuestion]:
    """获取所有已发布题目并随机打乱顺序"""
    questions = get_published_questions(db)
    random.shuffle(questions)
    return questions


def create_question(
    db: Session,
    question: str,
    options: list[str],
    correct_index: int,
    explanation: str | None = None,
    order: int = 0,
    is_published: bool = True,
) -> QuizQuestion:
    """创建题目"""
    q = QuizQuestion(
        question=question,
        options=json.dumps(options, ensure_ascii=False),
        correct_index=correct_index,
        explanation=explanation,
        order=order,
        is_published=is_published,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def update_question(
    db: Session,
    question_obj: QuizQuestion,
    question: str,
    options: list[str],
    correct_index: int,
    explanation: str | None = None,
    order: int = 0,
    is_published: bool = True,
) -> QuizQuestion:
    """更新题目"""
    question_obj.question = question
    question_obj.options = json.dumps(options, ensure_ascii=False)
    question_obj.correct_index = correct_index
    question_obj.explanation = explanation
    question_obj.order = order
    question_obj.is_published = is_published
    db.commit()
    db.refresh(question_obj)
    return question_obj


def toggle_publish(db: Session, question_obj: QuizQuestion) -> bool:
    """切换题目的发布状态，返回新状态"""
    question_obj.is_published = not question_obj.is_published
    db.commit()
    db.refresh(question_obj)
    return question_obj.is_published


def update_image(db: Session, question_obj: QuizQuestion, image_url: str | None) -> None:
    """更新题目的图片 URL"""
    question_obj.image_url = image_url
    db.commit()


def update_option_images(db: Session, question_obj: QuizQuestion, option_images: list[str | None]) -> None:
    """更新选项配图"""
    question_obj.option_images = json.dumps(option_images, ensure_ascii=False)
    db.commit()


def delete_question(db: Session, question_obj: QuizQuestion) -> None:
    """删除题目"""
    db.delete(question_obj)
    db.commit()


def submit_answers(
    db: Session,
    answers: list[dict],
    player_name: str | None = None,
) -> dict:
    """提交答案并评分"""
    total = len(answers)
    score = 0
    details = []

    for answer in answers:
        q_id = answer.get("q_id")
        selected = answer.get("selected")

        question_obj = db.query(QuizQuestion).filter(QuizQuestion.id == q_id).first()
        if not question_obj:
            continue

        options = json.loads(question_obj.options)
        is_correct = selected == question_obj.correct_index

        if is_correct:
            score += 1

        details.append({
            "q_id": question_obj.id,
            "question": question_obj.question,
            "options": options,
            "correct_index": question_obj.correct_index,
            "selected": selected,
            "is_correct": is_correct,
            "explanation": question_obj.explanation,
        })

    # 记录本次尝试
    attempt = QuizAttempt(
        player_name=player_name,
        score=score,
        total=total,
        answers=json.dumps(answers, ensure_ascii=False),
    )
    db.add(attempt)
    db.commit()

    percentage = round((score / total) * 100) if total > 0 else 0

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "details": details,
    }


def get_attempts(db: Session, limit: int = 10) -> list[QuizAttempt]:
    """获取最近的尝试记录"""
    return (
        db.query(QuizAttempt)
        .order_by(desc(QuizAttempt.created_at))
        .limit(limit)
        .all()
    )
