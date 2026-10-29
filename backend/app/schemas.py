from datetime import date

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    world_id: int | None = None
    difficulty: int = Field(ge=1, le=3)
    skill_ids: list[int] | None = Field(default=None, min_length=1, max_length=20)   # bỏ trống = mọi kỹ năng Rules cho phép ở độ khó này
    topic: str | None = Field(default=None, max_length=100)
    quantity: int | None = Field(default=None, ge=1, le=30)
    requested_count: int | None = Field(default=None, ge=1, le=30)
    auto_run: bool = False
    sync_run: bool = False



class ApproveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected_run_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class RejectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)


class RetireBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=500)


class RestoreBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=500)


class SourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_source: bool


class SettingBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int | float | str | bool | dict[str, StrictInt]


class WeeklySetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    week_start: date
    title: str | None = Field(default=None, min_length=1, max_length=100)


class WeeklyItemsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_ids: list[int] = Field(min_length=1, max_length=100)


class DraftEditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=3, max_length=200)
    question: str | None = Field(default=None, min_length=20, max_length=4000)
    note: str | None = Field(default=None, max_length=500)


class RequeueBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=500)


# ===== Auth, Profile & Submissions (Nguyên + Đạt) =====
class RegisterBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=5, max_length=255)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=1000)
    avatar_url: str | None = Field(default=None, max_length=500)


class PasswordChangeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AdminUserUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str | None = Field(default=None, pattern="^(learner|admin)$")
    status: str | None = Field(default=None, pattern="^(active|locked)$")


class SqlRunBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: int
    sql: str = Field(min_length=1, max_length=20000)


class AiCoachBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: int
    sql: str = Field(default="", max_length=20000)
    mode: str = Field(default="review", pattern="^(review|nl2sql|interview|autofix)$")
    prompt: str | None = Field(default=None, max_length=500)
    error_context: str | None = Field(default=None, max_length=1000)



