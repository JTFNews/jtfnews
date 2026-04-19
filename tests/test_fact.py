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


def test_canonical_json_is_deterministic(sample_fact_dict):
    shuffled = dict(reversed(list(sample_fact_dict.items())))
    assert (
        fact_module.canonical_json(sample_fact_dict)
        == fact_module.canonical_json(shuffled)
    )


def test_canonical_json_has_no_whitespace_padding():
    # Use a minimal dict whose values contain no prose, so we test only
    # structural separators.  Separators must be (",", ":") with no spaces.
    minimal = {"z": 1, "a": 2, "m": 3}
    s = fact_module.canonical_json(minimal)
    assert s == '{"a":2,"m":3,"z":1}'


def test_canonical_json_handles_nested_dicts(sample_fact_dict):
    # Reorder a nested dict and confirm canonical output is unchanged.
    reordered = copy_deep(sample_fact_dict)
    reordered["server"] = dict(reversed(list(sample_fact_dict["server"].items())))
    assert fact_module.canonical_json(sample_fact_dict) == fact_module.canonical_json(reordered)


def copy_deep(d):
    import copy
    return copy.deepcopy(d)
