from sqlalchemy import text

from lab.config import get_settings
from lab.db import engine


def test_engine_url_matches_settings():
    assert engine.url.render_as_string(hide_password=False) == get_settings().DATABASE_URL


def test_engine_can_connect_and_query():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()

    assert result == 1
