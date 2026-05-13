from datetime import UTC, datetime
from decimal import Decimal

import factory

from lab.models import Measurement, MeasurementKind
from tests.factories._base import _ModelFactory
from tests.factories.experiment import ExperimentFactory
from tests.factories.researcher import ResearcherFactory


# Three measurement factories — one per kind. Each populates the kind-specific
# columns and leaves the others NULL (matching the CHECK constraint). No
# ``sqlalchemy_get_or_create``: tests need to verify the CHECK by trying invalid
# combinations, which means each factory call must INSERT (not short-circuit).


class NumericMeasurementFactory(_ModelFactory):
    class Meta:
        model = Measurement
        sqlalchemy_session_persistence = "flush"

    experiment_id = factory.LazyAttribute(lambda obj: ExperimentFactory().id)
    recorded_by = factory.LazyAttribute(lambda obj: ResearcherFactory().id)
    recorded_at = factory.LazyFunction(lambda: datetime.now(UTC))
    kind = MeasurementKind.NUMERIC
    numeric_value = Decimal("7.5")
    unit = "mg/dL"


class CategoricalMeasurementFactory(_ModelFactory):
    class Meta:
        model = Measurement
        sqlalchemy_session_persistence = "flush"

    experiment_id = factory.LazyAttribute(lambda obj: ExperimentFactory().id)
    recorded_by = factory.LazyAttribute(lambda obj: ResearcherFactory().id)
    recorded_at = factory.LazyFunction(lambda: datetime.now(UTC))
    kind = MeasurementKind.CATEGORICAL
    categorical_value = "positive"


class TextMeasurementFactory(_ModelFactory):
    class Meta:
        model = Measurement
        sqlalchemy_session_persistence = "flush"

    experiment_id = factory.LazyAttribute(lambda obj: ExperimentFactory().id)
    recorded_by = factory.LazyAttribute(lambda obj: ResearcherFactory().id)
    recorded_at = factory.LazyFunction(lambda: datetime.now(UTC))
    kind = MeasurementKind.TEXT
    text_value = "Sample appeared cloudy."
