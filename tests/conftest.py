import pytest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An empty working directory with its own ``$HOME``.

    Alias lookup reads ``./.pksql`` and ``~/.pksql``, so tests must not see
    (or write to) the real ones.
    """
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.chdir(work)
    return work
