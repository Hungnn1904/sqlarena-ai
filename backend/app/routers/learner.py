"""API người học: bộ đề tuần PUBLISHED, chạy thử SQL sandbox, nộp bài chấm điểm, tiến độ kỹ năng & BXH tuần/tháng."""
from fastapi import APIRouter, Depends, Query

from ..db import begin
from ..schemas import AiCoachBody, SqlRunBody
from ..security import current_user
from ..services import questions as qsvc
from ..services import submissions as sub_svc
from ..services import weekly

router = APIRouter(tags=["learner-weekly"], dependencies=[Depends(current_user)])


@router.get("/weekly/current")
def weekly_current(user: dict = Depends(current_user)):
    with begin() as conn:
        return weekly.learner_view(conn, user["user_id"])


@router.get("/weekly/current/questions")
def weekly_current_questions(
    difficulty: int | None = Query(None, ge=1, le=3),
    skill_id: int | None = Query(None),
    solved: bool | None = Query(None),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: dict = Depends(current_user),
):
    with begin() as conn:
        return weekly.learner_questions(conn, difficulty, skill_id, solved, q, page, page_size, user["user_id"])


@router.get("/weekly/history")
def weekly_history(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    with begin() as conn:
        return weekly.learner_history(conn, page, page_size)


@router.get("/questions/{question_id}")
def get_question(question_id: int, user: dict = Depends(current_user)):
    with begin() as conn:
        return weekly.learner_question(conn, question_id, user["user_id"])


@router.get("/questions/{question_id}/submissions", tags=["learner-sandbox"])
def get_question_submissions(question_id: int, user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.question_submissions(conn, user["user_id"], question_id)


@router.get("/dataset/schema")
def dataset_schema():
    with begin() as conn:
        return qsvc.dataset_schema(conn)


@router.post("/sql/run", tags=["learner-sandbox"])
def run_sql(body: SqlRunBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.run_query(conn, user["user_id"], body.question_id, body.sql)


@router.post("/sql/explain", tags=["learner-sandbox"])
def explain_sql(body: SqlRunBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.explain_query(conn, body.question_id, body.sql)


@router.post("/sql/ai-coach", tags=["learner-sandbox"])
def ai_coach_sql(body: AiCoachBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.ai_coach_assist(
            conn, body.question_id, body.sql, body.mode, body.prompt, body.error_context
        )




@router.post("/submissions", tags=["learner-sandbox"])
def submit_sql(body: SqlRunBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.submit_query(conn, user["user_id"], body.question_id, body.sql)


@router.get("/progress", tags=["learner-progress"])
def my_progress(user: dict = Depends(current_user)):
    with begin() as conn:
        return sub_svc.user_progress(conn, user["user_id"])


@router.get("/leaderboard/weekly", tags=["learner-leaderboard"])
def leaderboard_weekly(set_id: int | None = Query(None)):
    with begin() as conn:
        return sub_svc.weekly_leaderboard(conn, set_id)


@router.get("/leaderboard/monthly", tags=["learner-leaderboard"])
def leaderboard_monthly(year: int | None = Query(None), month: int | None = Query(None)):
    with begin() as conn:
        return sub_svc.monthly_leaderboard(conn, year, month)

