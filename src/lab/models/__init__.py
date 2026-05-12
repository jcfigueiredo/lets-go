"""Aggregate root re-exports.

This module is the single import point for ``SQLModel.metadata`` discovery,
used by Alembic's ``env.py`` (Task 6). As aggregates land with the schema
design, import them here so their table metadata is registered before
autogenerate runs.
"""

from sqlmodel import SQLModel

__all__ = ["SQLModel"]
