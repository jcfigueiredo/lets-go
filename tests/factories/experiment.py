import factory

from lab.models import Experiment, ExperimentStatus
from tests.factories._base import _ModelFactory
from tests.factories.project import ProjectFactory


class ExperimentFactory(_ModelFactory):
    # No UNIQUE constraints on Experiment, so omit ``sqlalchemy_get_or_create``
    # (we want fresh experiments per factory call). Tests that need a specific
    # experiment construct it with explicit fields.
    class Meta:
        model = Experiment
        sqlalchemy_session_persistence = "flush"

    project_id = factory.LazyAttribute(lambda obj: ProjectFactory().id)
    title = factory.Sequence(lambda n: f"Experiment {n}")
    hypothesis = factory.Faker("sentence", nb_words=8)
    status = ExperimentStatus.PLANNED
