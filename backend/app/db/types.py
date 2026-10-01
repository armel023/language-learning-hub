import enum

from sqlalchemy import Enum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Store the enum's string VALUE in Postgres instead of SQLAlchemy's default (the member NAME)."""
    return Enum(enum_cls, name=name, values_callable=lambda obj: [e.value for e in obj])
