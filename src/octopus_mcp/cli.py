"""CLI: serve | configure | resync | version."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from octopus_mcp import __version__


def _run_serve() -> int:
    from octopus_mcp.server import run

    return run()


def _run_configure(args: argparse.Namespace) -> int:
    try:
        import keyring
    except ImportError:
        print("`keyring` not installed. pip install keyring", file=sys.stderr)
        return 1

    profile = args.profile or "default"
    service = f"octopus-mcp:{profile}"
    api_key = getpass.getpass("Octopus API key: ").strip()
    account = input("Account number (A-XXXXXXXX): ").strip()
    email = input("Email (optional, for Kraken): ").strip() or None
    password = getpass.getpass("Password (optional, for Kraken): ").strip() or None

    if api_key:
        keyring.set_password(service, "api_key", api_key)
    if account:
        keyring.set_password(service, "account_number", account)
    if email:
        keyring.set_password(service, "email", email)
    if password:
        keyring.set_password(service, "password", password)

    print(f"Saved credentials to OS keyring under service '{service}'")
    return 0


def _run_resync(args: argparse.Namespace) -> int:
    import sqlite3

    from platformdirs import user_cache_dir

    db_path = Path(user_cache_dir("octopus-mcp")) / "cache.db"
    if not db_path.exists():
        print(f"No cache at {db_path}; nothing to do.")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        if args.resource == "all":
            for tbl in (
                "consumption",
                "unit_rates",
                "standing_charges",
                "products",
                "saving_sessions",
                "octoplus_events",
                "sync_state",
            ):
                conn.execute(f"DELETE FROM {tbl}")
        elif args.resource == "consumption":
            conn.execute("DELETE FROM consumption")
            conn.execute("DELETE FROM sync_state WHERE resource LIKE 'consumption:%'")
        else:
            print(f"Unknown resource: {args.resource}", file=sys.stderr)
            return 1
        conn.commit()
    finally:
        conn.close()
    print(f"Cleared {args.resource}.")
    return 0


def _run_version(_: argparse.Namespace) -> int:
    print(f"octopus-mcp {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="octopus-mcp")
    sub = parser.add_subparsers(dest="cmd")

    serve_p = sub.add_parser("serve", help="Run the MCP server over stdio (default)")
    serve_p.set_defaults(func=lambda _args: _run_serve())

    cfg = sub.add_parser("configure", help="Interactively store credentials in OS keyring")
    cfg.add_argument("--profile", default="default")
    cfg.set_defaults(func=_run_configure)

    rs = sub.add_parser("resync", help="Drop cached data and re-pull on next call")
    rs.add_argument("--resource", choices=["all", "consumption"], default="all")
    rs.set_defaults(func=_run_resync)

    v = sub.add_parser("version", help="Print version")
    v.set_defaults(func=_run_version)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.cmd:
        return _run_serve()
    return int(args.func(args) or 0)
