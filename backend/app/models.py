from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Child(Base):
    __tablename__ = "child"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="child")


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True)
    # stable identifier the problem generator targets, e.g. "addition_1digit"
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(255))

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="skill")


class Attempt(Base):
    __tablename__ = "attempt"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    difficulty: Mapped[int]
    correct: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    child: Mapped["Child"] = relationship(back_populates="attempts")
    skill: Mapped["Skill"] = relationship(back_populates="attempts")
