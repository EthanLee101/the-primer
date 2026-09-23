from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.mastery import INITIAL_DIFFICULTY


class Parent(Base):
    __tablename__ = "parent"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    children: Mapped[list["Child"]] = relationship(back_populates="parent")


class Child(Base):
    __tablename__ = "child"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # nullable: children created through the existing unauthenticated
    # "what's your name?" flow (increments 6/7) have no parent account yet —
    # only children created while a parent session is active get linked
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("parent.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    parent: Mapped["Parent | None"] = relationship(back_populates="children")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="child")


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(primary_key=True)
    # stable identifier the problem generator targets, e.g. "addition" (see app/problems.py)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(255))

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="skill")


class Attempt(Base):
    __tablename__ = "attempt"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    difficulty: Mapped[int]
    operand_a: Mapped[int]
    operand_b: Mapped[int]
    # null until the child answers; grading happens against these operands,
    # never against values the client sends back at answer time
    submitted_answer: Mapped[int | None] = mapped_column(default=None)
    correct: Mapped[bool | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    answered_at: Mapped[datetime | None] = mapped_column(default=None)

    child: Mapped["Child"] = relationship(back_populates="attempts")
    skill: Mapped["Skill"] = relationship(back_populates="attempts")


class Mastery(Base):
    """Current adaptive state for one child on one skill — the difficulty to
    serve next and the rolling accuracy that drives it. One row per
    (child, skill), created lazily the first time that pair is seen."""

    __tablename__ = "mastery"
    __table_args__ = (UniqueConstraint("child_id", "skill_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"))
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id"))
    difficulty: Mapped[int] = mapped_column(default=INITIAL_DIFFICULTY)
    rolling_accuracy: Mapped[float | None] = mapped_column(default=None)
    attempts_count: Mapped[int] = mapped_column(default=0)
    correct_count: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    child: Mapped["Child"] = relationship()
    skill: Mapped["Skill"] = relationship()
