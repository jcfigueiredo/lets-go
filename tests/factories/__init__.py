"""Test factories.

Each factory inherits from ``_ModelFactory`` in ``_base.py`` and is registered
in ``ALL_FACTORIES`` here. The conftest ``factories`` fixture binds them to
the per-test SAVEPOINT-isolated session.

To add a factory for a new aggregate:
1. Create ``tests/factories/<entity>.py`` with a ``<Entity>Factory`` class
2. Append it to ``ALL_FACTORIES`` here
3. Add a line to ``factory_namespace()`` so tests can use ``factories.<entity>``
"""

from types import SimpleNamespace

from tests.factories.experiment import ExperimentFactory
from tests.factories.project import ProjectFactory
from tests.factories.researcher import ResearcherFactory
from tests.factories.sample import SampleFactory

ALL_FACTORIES: list[type] = [
    ExperimentFactory,
    ProjectFactory,
    ResearcherFactory,
    SampleFactory,
]


def factory_namespace() -> SimpleNamespace:
    """Return a namespace exposing each factory by snake-case name."""
    return SimpleNamespace(
        experiment=ExperimentFactory,
        project=ProjectFactory,
        researcher=ResearcherFactory,
        sample=SampleFactory,
    )
