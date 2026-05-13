from datetime import UTC, datetime

import factory

from lab.models import Sample
from tests.factories._base import _ModelFactory


class SampleFactory(_ModelFactory):
    class Meta:
        model = Sample
        sqlalchemy_session_persistence = "flush"

    accession_code = factory.Sequence(lambda n: f"SAMPLE-{n:06d}")
    specimen_type = "blood"
    collected_at = factory.LazyFunction(lambda: datetime.now(UTC))
    storage_location = "Freezer A / Shelf 2 / Box 3"
