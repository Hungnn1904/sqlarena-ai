"""API người học: chỉ thấy câu hỏi thuộc bộ đề tuần đang PUBLISHED. Không bao giờ trả reference_sql / expected_result."""
from fastapi import APIRouter, Depends, Query

from ..db import begin
from ..security import current_user
from ..services import questions as qsvc
from ..services import weekly

router = APIRouter(tags=["learner-weekly"], dependencies=[Depends(current_user)])


@router.get("/weekly/current")
def weekly_current():
    with begin() as conn:
        return weekly.learner_view(conn)


@router.get("/weekly/current/questions")
def weekly_current_questions(difficulty: int | None = Query(None, ge=1, le=3), skill_id: int | None = None, solved: bool | None = None, q: str | None = Query(None, max_length=100),
                             page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    with begin() as conn:
        return weekly.learner_questions(conn, difficulty, skill_id, solved, q, page, page_size)


@router.get("/weekly/history")
def weekly_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return weekly.learner_history(conn, page, page_size)


@router.get("/questions/{question_id}")
def get_question(question_id: int):
    with begin() as conn:
        return weekly.learner_question(conn, question_id)


@router.get("/dataset/schema")
def dataset_schema():
    with begin() as conn:
        return qsvc.dataset_schema(conn)
