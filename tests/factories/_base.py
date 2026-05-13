"""Base class for all factory-boy factories.

Subclasses set ``Meta.model`` to their SQLModel class. The conftest
``factories`` fixture sets ``sqlalchemy_session`` on each registered
factory before yielding the namespace.
"""

from factory.alchemy import SQLAlchemyModelFactory


class _ModelFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"
