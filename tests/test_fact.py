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


def test_compute_fact_id_is_deterministic(sample_fact_dict):
    id1 = fact_module.compute_fact_id(sample_fact_dict)
    id2 = fact_module.compute_fact_id(sample_fact_dict)
    assert id1 == id2
    assert id1.startswith("sha256:")
    assert len(id1) == len("sha256:") + 64


def test_compute_fact_id_changes_when_fact_text_changes(sample_fact_dict):
    original = fact_module.compute_fact_id(sample_fact_dict)
    sample_fact_dict["fact"] = "The vote was 141 to 9."
    changed = fact_module.compute_fact_id(sample_fact_dict)
    assert original != changed


def test_compute_fact_id_ignores_signature_field(sample_fact_dict):
    original = fact_module.compute_fact_id(sample_fact_dict)
    sample_fact_dict["signature"] = "different-signature"
    assert fact_module.compute_fact_id(sample_fact_dict) == original
