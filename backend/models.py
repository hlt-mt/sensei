from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    protected_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    data: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped[User] = relationship("User", back_populates="projects")
