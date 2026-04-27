import sys

import pytest

from octopus_mcp import __version__
from octopus_mcp.cli import build_parser, main


def test_version_subcommand_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(["version"])
    args.func(args)
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_lists_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    out = capsys.readouterr().out
    for cmd in ("serve", "configure", "resync", "version"):
        assert cmd in out


def test_main_with_no_args_invokes_serve(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"served": False}

    def fake_run() -> int:
        called["served"] = True
        return 0

    monkeypatch.setattr("octopus_mcp.cli._run_serve", fake_run)
    monkeypatch.setattr(sys, "argv", ["octopus-mcp"])
    rc = main()
    assert rc == 0 and called["served"]
