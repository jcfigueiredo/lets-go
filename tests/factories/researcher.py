import factory

from lab.models import Researcher, ResearcherRole
from tests.factories._base import _ModelFactory


class ResearcherFactory(_ModelFactory):
    class Meta:
        model = Researcher

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"researcher-{n}@lab.example")
    role = ResearcherRole.LAB_TECHNICIAN
