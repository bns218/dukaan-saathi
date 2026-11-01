import os

import pytest

# Offline test env — must be set before importing app modules.
os.environ["MOCK_META"] = "1"


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Each test gets its own empty database."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
