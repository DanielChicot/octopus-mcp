from octopus_mcp import __version__


def test_version_is_set():
    assert __version__
    assert isinstance(__version__, str)
