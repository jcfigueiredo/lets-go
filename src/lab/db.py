"""SQLAlchemy engine bound to the runtime DATABASE_URL.

The engine is created at import time and shared process-wide. Tests
share the same engine factory but bind it to ``TEST_DATABASE_URL`` via
their session fixture (see ``tests/conftest.py`` in Task 7).
"""

from sqlalchemy import create_engine

from lab.config import get_settings

engine = create_engine(get_settings().DATABASE_URL, future=True)
