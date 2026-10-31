import json

from corpus_support import ROOT


def test_loader_rejects_missing_or_null_optional_sections(tmp_path):
    from scripts.load_sqlite import load
    import pytest

    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    for table, key in [("requirements", "implementation_notes"), ("decisions", "alternatives")]:
        for missing in (False, True):
            payload = json.loads(json.dumps(fixture))
            if missing:
                del payload[table][0][key]
            else:
                payload[table][0][key] = None
            with pytest.raises(ValueError) as error:
                load(payload, tmp_path / "invalid.sqlite")
            assert key in str(error.value)
