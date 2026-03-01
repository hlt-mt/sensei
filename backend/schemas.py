from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=1)
    admin: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=1)
    admin: Optional[bool] = None


class UserOut(UserBase):
    id: int
    admin: bool
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    data: str = ""


class ProjectCreate(ProjectBase):
    user_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    data: Optional[str] = None
    user_id: Optional[int] = None


class ProjectOut(ProjectBase):
    id: int
    user_id: int
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)


class MeOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    admin: bool
