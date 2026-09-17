import pytest

from app.data.seed import reset_store
from app.data.store import store as global_store


@pytest.fixture()
def s():
    """Fresh, deterministic synthetic dataset for every test."""
    return reset_store()


@pytest.fixture()
def store():
    return global_store
