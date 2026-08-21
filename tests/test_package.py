import re
from pathlib import Path

import pytest

import pksql

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


@pytest.mark.skipif(not PYPROJECT.exists(), reason="running against an installed copy")
def test_version_matches_pyproject():
    """A release bumps both, and they have silently drifted apart before."""
    declared = re.search(r'^version = "([^"]+)"', PYPROJECT.read_text(), re.M)
    assert declared is not None
    assert pksql.__version__ == declared.group(1)
