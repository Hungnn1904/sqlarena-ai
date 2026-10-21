from datetime import date

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    world_id: int | None = None
    difficulty: int = Field(ge=1, le=3)
    skill_ids: list[int] | None = Field(default=None, min_length=1, max_length=20)   # bỏ trống = mọi kỹ năng Rules cho phép ở độ khó này
    topic: str | None = Field(default=None, max_length=100)
    quantity: int = Field(ge=1, le=30)


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
