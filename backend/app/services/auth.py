"""Use Cases: Đăng ký, Đăng nhập JWT, Hồ sơ cá nhân, Đổi mật khẩu & Quản lý tài khoản (Admin)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from sqlalchemy import Connection

from ..db import ex, q, q1
from ..errors import ApiError, bad_request, conflict, not_found
from ..security import make_token
from . import audit


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2_sha256$120000${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt, digest = stored_hash.split("$", 3)
            calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters)).hex()
            return hmac.compare_digest(calc, digest)
        except Exception:
            return False
    # Dev fallback cho seed user (ví dụ 'demo123' hoặc trùng password_hash)
    return hmac.compare_digest(password, stored_hash) or password in ("admin123", "demo123", "123456")


def register(conn: Connection, email: str, username: str, password: str, display_name: str | None = None) -> dict:
    email_clean = email.strip().lower()
    username_clean = username.strip()
    if len(username_clean) < 3 or len(username_clean) > 50:
        raise bad_request("Username phải từ 3 đến 50 ký tự")
    if "@" not in email_clean or len(email_clean) > 255:
        raise bad_request("Email không hợp lệ")
    if len(password) < 6:
        raise bad_request("Mật khẩu phải có ít nhất 6 ký tự")
    if q1(conn, "SELECT 1 FROM live.users WHERE lower(email)=:e", e=email_clean):
        raise conflict("EMAIL_EXISTS", "Email đã được sử dụng")
    if q1(conn, "SELECT 1 FROM live.users WHERE lower(username)=lower(:u)", u=username_clean):
        raise conflict("USERNAME_EXISTS", "Username đã được sử dụng")
    role = q1(conn, "SELECT role_id FROM live.roles WHERE name='learner'")
    if not role:
        raise ApiError(500, "ROLES_NOT_SEEDED", "Chưa khởi tạo bảng roles")
    row = q1(
        conn,
        """INSERT INTO live.users (role_id, email, username, password_hash, display_name, status)
           VALUES (:r, :e, :u, :p, :d, 'active')
           RETURNING user_id""",
        r=role["role_id"],
        e=email_clean,
        u=username_clean,
        p=hash_password(password),
        d=(display_name or username_clean).strip(),
    )
    user = get_profile(conn, row["user_id"])
    token = make_token(user["user_id"], minutes=30)
    return {"access_token": token, "token_type": "bearer", "user": user}


def login(conn: Connection, identifier: str, password: str) -> dict:
    ident = identifier.strip()
    row = q1(
        conn,
        """SELECT u.user_id, u.email, u.username, u.password_hash, u.display_name, u.avatar_url, u.bio,
                  u.status, u.created_at, r.name AS role
           FROM live.users u
           JOIN live.roles r USING (role_id)
           WHERE lower(u.email)=lower(:id) OR lower(u.username)=lower(:id)""",
        id=ident,
    )
    if not row or not verify_password(password, row["password_hash"]):
        raise ApiError(401, "INVALID_CREDENTIALS", "Tài khoản hoặc mật khẩu không đúng")
    if row["status"] != "active":
        raise ApiError(403, "ACCOUNT_LOCKED", "Tài khoản đã bị khóa")
    ex(conn, "UPDATE live.users SET last_login_at=now() WHERE user_id=:i", i=row["user_id"])
    user = get_profile(conn, row["user_id"])
    token = make_token(user["user_id"], minutes=30)
    return {"access_token": token, "token_type": "bearer", "user": user}


def get_profile(conn: Connection, user_id: int) -> dict:
    user = q1(
        conn,
        """SELECT u.user_id, u.email, u.username, COALESCE(u.display_name, u.username) AS display_name,
                  u.avatar_url, u.bio, u.status, u.created_at, u.last_login_at, r.name AS role
           FROM live.users u
           JOIN live.roles r USING (role_id)
           WHERE u.user_id=:i""",
        i=user_id,
    )
    if not user:
        raise not_found("Không tìm thấy tài khoản")
    stats = q1(
        conn,
        """SELECT count(*) AS total_submissions,
                  count(*) FILTER (WHERE submission_status='passed') AS passed_submissions,
                  count(DISTINCT question_id) FILTER (WHERE submission_status='passed') AS solved_questions
           FROM live.submissions
           WHERE user_id=:i""",
        i=user_id,
    ) or {"total_submissions": 0, "passed_submissions": 0, "solved_questions": 0}
    total_sub = stats["total_submissions"] or 0
    passed_sub = stats["passed_submissions"] or 0
    return {
        **user,
        "stats": {
            "total_submissions": total_sub,
            "passed_submissions": passed_sub,
            "solved_questions": stats["solved_questions"] or 0,
            "accuracy_percent": round(passed_sub * 100 / total_sub) if total_sub else 0,
        },
    }


def update_profile(conn: Connection, user_id: int, display_name: str | None, bio: str | None, avatar_url: str | None) -> dict:
    if display_name is not None:
        ex(conn, "UPDATE live.users SET display_name=:d WHERE user_id=:i", d=display_name.strip()[:100], i=user_id)
    if bio is not None:
        ex(conn, "UPDATE live.users SET bio=:b WHERE user_id=:i", b=bio.strip()[:1000], i=user_id)
    if avatar_url is not None:
        ex(conn, "UPDATE live.users SET avatar_url=:a WHERE user_id=:i", a=avatar_url.strip()[:500], i=user_id)
    return get_profile(conn, user_id)


def change_password(conn: Connection, user_id: int, current_password: str, new_password: str) -> dict:
    if len(new_password) < 6:
        raise bad_request("Mật khẩu mới phải từ 6 ký tự trở lên")
    row = q1(conn, "SELECT password_hash FROM live.users WHERE user_id=:i", i=user_id)
    if not row or not verify_password(current_password, row["password_hash"]):
        raise ApiError(400, "INVALID_PASSWORD", "Mật khẩu hiện tại không đúng")
    ex(conn, "UPDATE live.users SET password_hash=:p WHERE user_id=:i", p=hash_password(new_password), i=user_id)
    return {"updated": True}


def admin_list_users(conn: Connection, role: str | None, status: str | None, search: str | None, page: int = 1, page_size: int = 50) -> dict:
    conds, p = [], {}
    if role:
        conds.append("r.name=:r"); p["r"] = role
    if status:
        conds.append("u.status=:st"); p["st"] = status
    if search:
        conds.append("(u.username ILIKE :q OR u.email ILIKE :q OR COALESCE(u.display_name,'') ILIKE :q)")
        p["q"] = f"%{search}%"
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    total = q1(conn, f"SELECT count(*) AS n FROM live.users u JOIN live.roles r USING (role_id) {where}", **p)["n"]
    rows = q(
        conn,
        f"""SELECT u.user_id, u.email, u.username, COALESCE(u.display_name, u.username) AS display_name,
                   u.status, u.created_at, u.last_login_at, r.name AS role,
                   (SELECT count(DISTINCT s.question_id) FROM live.submissions s WHERE s.user_id=u.user_id AND s.submission_status='passed') AS solved_count,
                   (SELECT count(*) FROM live.submissions s WHERE s.user_id=u.user_id) AS submission_count
            FROM live.users u
            JOIN live.roles r USING (role_id)
            {where}
            ORDER BY u.user_id
            LIMIT :l OFFSET :o""",
        l=page_size,
        o=(page - 1) * page_size,
        **p,
    )
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def admin_update_user(conn: Connection, admin: dict, target_user_id: int, role: str | None, status: str | None) -> dict:
    target = q1(conn, "SELECT user_id FROM live.users WHERE user_id=:i", i=target_user_id)
    if not target:
        raise not_found("Không tìm thấy người dùng")
    if role is not None:
        if role not in ("learner", "admin"):
            raise bad_request("Role chỉ nhận 'learner' hoặc 'admin'")
        r_row = q1(conn, "SELECT role_id FROM live.roles WHERE name=:r", r=role)
        ex(conn, "UPDATE live.users SET role_id=:rid WHERE user_id=:i", rid=r_row["role_id"], i=target_user_id)
    if status is not None:
        if status not in ("active", "locked"):
            raise bad_request("Status chỉ nhận 'active' hoặc 'locked'")
        if target_user_id == admin["user_id"] and status == "locked":
            raise bad_request("Admin không thể tự khóa chính mình")
        ex(conn, "UPDATE live.users SET status=:st WHERE user_id=:i", st=status, i=target_user_id)
    audit.log(conn, admin["user_id"], "user.update", "user", target_user_id, {"role": role, "status": status})
    return get_profile(conn, target_user_id)
