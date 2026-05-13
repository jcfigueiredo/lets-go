import factory

from lab.models import Researcher, ResearcherRole
from tests.factories._base import _ModelFactory


class ResearcherFactory(_ModelFactory):
    # `email` is UNIQUE in the schema; omit ``sqlalchemy_get_or_create`` so
    # duplicate-constraint tests can raise IntegrityError (with get_or_create,
    # factory-boy short-circuits the second call and the test would never raise).
    class Meta:
        model = Researcher

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"researcher-{n}@lab.example")
    role = ResearcherRole.LAB_TECHNICIAN
