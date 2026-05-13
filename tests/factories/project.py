import factory

from lab.models import Project, ProjectStatus
from tests.factories._base import _ModelFactory


class ProjectFactory(_ModelFactory):
    class Meta:
        model = Project
        sqlalchemy_session_persistence = "flush"
        sqlalchemy_get_or_create = ("title",)

    title = factory.Sequence(lambda n: f"Project {n}")
    description = factory.Faker("paragraph", nb_sentences=2)
    status = ProjectStatus.PLANNING
