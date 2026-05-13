"""Aggregate root re-exports.

Single import point for ``SQLModel.metadata`` discovery, used by Alembic's
``env.py``. Every new aggregate is imported here so its table metadata is
registered before autogenerate runs.
"""

from sqlmodel import SQLModel

from lab.models.project import Project, ProjectStatus
from lab.models.researcher import Researcher, ResearcherRole

__all__ = ["SQLModel", "Project", "ProjectStatus", "Researcher", "ResearcherRole"]
