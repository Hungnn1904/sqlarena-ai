"""Xác thực JWT dùng chung với module Auth (HS256, claim `sub` = user_id).

Theo hợp đồng v7: role và trạng thái khóa luôn đọc lại từ DB mỗi request, không tin claim cũ.
Module Auth (Nguyên) chịu trách nhiệm cấp token; ở đây chỉ XÁC MINH token.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .db import begin, q1
from .errors import ApiError

_bearer = HTTPBearer(auto_error=False)


def make_token(user_id: int, minutes: int = 15) -> str:
    """Tạo access token (dùng cho test/dev; production do module Auth cấp)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=min(minutes, 30))},
                      s.jwt_secret, algorithm=s.jwt_algorithm)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if creds is None:
        raise ApiError(401, "UNAUTHORIZED", "Thiếu access token")
    s = get_settings()
    try:
        claims = jwt.decode(creds.credentials, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["sub", "exp"]})
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        raise ApiError(401, "UNAUTHORIZED", "Token không hợp lệ hoặc đã hết hạn")
    with begin() as conn:          # transaction ngắn, không giữ connection suốt request
        user = q1(conn, "SELECT u.user_id, u.status, r.name AS role FROM live.users u JOIN live.roles r USING (role_id) WHERE u.user_id=:i", i=user_id)
    if not user:
        raise ApiError(401, "UNAUTHORIZED", "Tài khoản không tồn tại")
    if user["status"] != "active":
        raise ApiError(403, "FORBIDDEN", "Tài khoản bị khóa")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise ApiError(403, "FORBIDDEN", "Cần quyền admin")
    return user
