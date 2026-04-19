"""Tests for jtfprotocol.fact."""
from jtfprotocol import fact as fact_module


def test_fact_from_dict_roundtrip(sample_fact_dict):
    f = fact_module.Fact.from_dict(sample_fact_dict)
    assert f.to_dict() == sample_fact_dict


def test_fact_rejects_wrong_jtf_version(sample_fact_dict):
    sample_fact_dict["jtf_version"] = 999
    import pytest

    with pytest.raises(ValueError, match="jtf_version"):
        fact_module.Fact.from_dict(sample_fact_dict)
