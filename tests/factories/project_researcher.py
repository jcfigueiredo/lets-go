import factory

from lab.models import ProjectResearcher
from tests.factories._base import _ModelFactory
from tests.factories.project import ProjectFactory
from tests.factories.researcher import ResearcherFactory


class ProjectResearcherFactory(_ModelFactory):
    class Meta:
        model = ProjectResearcher
        sqlalchemy_session_persistence = "flush"
        sqlalchemy_get_or_create = ("project_id", "researcher_id")

    project_id = factory.LazyAttribute(lambda obj: ProjectFactory().id)
    researcher_id = factory.LazyAttribute(lambda obj: ResearcherFactory().id)
