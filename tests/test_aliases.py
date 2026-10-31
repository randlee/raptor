from pathlib import Path
from scripts.qualify import Qualifier
import json

import pytest
from corpus_support import document, qualify
from corpus_support import ROOT


def test_declared_aliases_apply_after_normalization_and_are_counted(document):
    root, text = document
    (root / ".raptor/aliases.toml").write_text(
        '[labels]\nAcceptance = "Acceptance Criteria"\n'
        '[sections]\nStatement = "Requirement Statement"\n'
        '[values]\nReady = "Active"\nSHALL = "Must"\n'
    )
    text = text.replace("Acceptance Criteria", " aCcEpTaNcE : ").replace(
        "### Requirement Statement", "### Statement"
    )
    text = text.replace("Active", "Ready").replace("MUST statements", "SHALL statements")
    result = qualify(root, text)
    assert result.issues == []
    assert result.counts == {
        "labels": {"Acceptance -> Acceptance Criteria": 1},
        "sections": {"Statement -> Requirement Statement": 1},
        "values": {"Ready -> Active": 1, "SHALL -> Must": 1},
    }


@pytest.mark.parametrize(
    "config,line",
    [
        ('[labels]\n\nAcceptance = "No Such Label"\n', 3),
        ('[labels]\nShared = "Acceptance Criteria"\n[sections]\nShared = "No Such Section"\n', 4),
    ],
)
def test_unknown_alias_target_is_refused_before_markdown_is_read(
    document, monkeypatch, config, line
):
    root, _ = document
    alias = root / ".raptor/aliases.toml"
    alias.write_text(config)
    original = Path.read_text

    def guarded(path, *args, **kwargs):
        assert path.suffix != ".md", "invalid configuration must precede Markdown reads"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)
    with pytest.raises(ValueError, match=rf"aliases.toml:{line}: unknown alias target"):
        Qualifier(root)
