"""Aggregate root re-exports.

Single import point for ``SQLModel.metadata`` discovery, used by Alembic's
``env.py``. Every new aggregate is imported here so its table metadata is
registered before autogenerate runs.
"""

from sqlmodel import SQLModel

from lab.models.experiment import Experiment, ExperimentStatus
from lab.models.experiment_sample import ExperimentSample
from lab.models.measurement import Measurement, MeasurementKind
from lab.models.project import Project, ProjectStatus
from lab.models.project_researcher import ProjectResearcher
from lab.models.researcher import Researcher, ResearcherRole
from lab.models.sample import Sample

__all__ = [
    "SQLModel",
    "Experiment",
    "ExperimentStatus",
    "ExperimentSample",
    "Measurement",
    "MeasurementKind",
    "Project",
    "ProjectStatus",
    "ProjectResearcher",
    "Researcher",
    "ResearcherRole",
    "Sample",
]
