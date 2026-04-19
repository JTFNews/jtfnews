"""Shared pytest fixtures for jtfprotocol tests."""
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_fact_dict() -> dict:
    """A valid two-source fact matching the Phase 1 schema."""
    return json.loads((FIXTURES / "sample_fact.json").read_text())
