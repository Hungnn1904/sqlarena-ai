"""Router: Xác thực (Đăng ký, Đăng nhập), Hồ sơ cá nhân & Quản lý tài khoản (Admin)."""
from fastapi import APIRouter, Depends, Query

from ..db import begin
from ..schemas import AdminUserUpdateBody, LoginBody, PasswordChangeBody, ProfileUpdateBody, RegisterBody
from ..security import current_user, require_admin
from ..services import auth as auth_svc

router = APIRouter(tags=["auth"])


@router.post("/auth/register", status_code=201)
def register(body: RegisterBody):
    with begin() as conn:
        return auth_svc.register(conn, body.email, body.username, body.password, body.display_name)


@router.post("/auth/login")
def login(body: LoginBody):
    with begin() as conn:
        return auth_svc.login(conn, body.identifier, body.password)


@router.get("/auth/me")
def get_me(user: dict = Depends(current_user)):
    with begin() as conn:
        return auth_svc.get_profile(conn, user["user_id"])


@router.put("/auth/me")
def update_me(body: ProfileUpdateBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return auth_svc.update_profile(conn, user["user_id"], body.display_name, body.bio, body.avatar_url)


@router.post("/auth/change-password")
def change_password(body: PasswordChangeBody, user: dict = Depends(current_user)):
    with begin() as conn:
        return auth_svc.change_password(conn, user["user_id"], body.current_password, body.new_password)


@router.get("/admin/users", tags=["admin-users"], dependencies=[Depends(require_admin)])
def admin_users(
    role: str | None = Query(None, pattern="^(learner|admin)$"),
    status: str | None = Query(None, pattern="^(active|locked)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    with begin() as conn:
        return auth_svc.admin_list_users(conn, role, status, q, page, page_size)


@router.patch("/admin/users/{target_user_id}", tags=["admin-users"])
def admin_patch_user(target_user_id: int, body: AdminUserUpdateBody, admin: dict = Depends(require_admin)):
    with begin() as conn:
        return auth_svc.admin_update_user(conn, admin, target_user_id, body.role, body.status)
