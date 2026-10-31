"""Failure reporting for the shared bounded subprocess helper."""
import subprocess

import pytest
from corpus_support import run


def test_timeout_failure_identifies_the_script_and_arguments(monkeypatch):
    def timed_out(command, **options):
        assert options["timeout"] == 30
        assert options["stdin"] == subprocess.DEVNULL
        raise subprocess.TimeoutExpired(command, options["timeout"])

    monkeypatch.setattr(subprocess, "run", timed_out)
    with pytest.raises(pytest.fail.Exception) as caught:
        run("extract.py", "--example")
    assert "extract.py" in str(caught.value)
    assert "--example" in str(caught.value)
    assert "30s" in str(caught.value)
