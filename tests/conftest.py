"""Shared helpers for the tests: saved real answers and a fake of the mirror's fetch helpers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from mirrordash_skolmatsedel.providers.base import Net

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def fixture_json(name: str):
    return json.loads(fixture_bytes(name))


@pytest.fixture
def make_net():
    """make_net(json=(data, error), raw=(bytes, error)) -> a Net whose fetches give those answers."""
    def build(json=(None, "offline"), raw=(None, "offline")) -> Net:
        return Net(fetch_json=AsyncMock(return_value=json), fetch=AsyncMock(return_value=raw))
    return build
