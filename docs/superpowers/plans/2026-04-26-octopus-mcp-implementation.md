# Octopus MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `octopus-mcp` — a Python MCP server plus Claude Code plugin that lets Claude analyse an Octopus Energy account (consumption, billing, tariff comparisons, Saving Sessions, Octoplus).

**Architecture:** Layered Python package (`octopus → cache → analysis → tools → server`). Async `httpx` REST client + raw `httpx` GraphQL client for Kraken. Stdlib SQLite cache with WAL + incremental sync. Pure-function analysis layer. Pydantic-typed MCP tools. Sibling Claude Code plugin (manifest, `.mcp.json`, slash commands, skill) at the repo root.

**Tech Stack:** Python 3.11+, `mcp` SDK, `httpx`, `pydantic` v2, `python-dotenv`, `keyring`, `platformdirs`, `tenacity`, stdlib `sqlite3`. Tests: `pytest`, `pytest-asyncio`, `pytest-recording`, `pytest-cov`. Lint: `ruff` + `mypy --strict`. Build: `hatchling`.

**Spec:** `docs/superpowers/specs/2026-04-26-octopus-mcp-design.md`

**Phasing:** MVP = Phases 0–5 (REST-only path: bill, tariff comparison, peaks, breakdowns, plugin slash commands minus saving-sessions). Phase 6 adds Kraken (Saving Sessions / Octoplus). Phase 7 finishes plugin polish + release.

---

## Phase 0 — Project skeleton & tooling

### Task 1: pyproject.toml + package skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/octopus_mcp/__init__.py`
- Create: `src/octopus_mcp/cli.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

`tests/test_smoke.py`:
```python
from octopus_mcp import __version__


def test_version_is_set():
    assert __version__
    assert isinstance(__version__, str)
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "octopus-mcp"
version = "0.1.0"
description = "MCP server for Octopus Energy account analysis"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "Daniel Chicot" }]
keywords = ["mcp", "octopus-energy", "claude"]
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
    "pydantic>=2.7",
    "python-dotenv>=1.0",
    "keyring>=25",
    "platformdirs>=4",
    "tenacity>=8",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "pytest-recording>=0.13",
    "ruff>=0.4",
    "mypy>=1.10",
    "pre-commit>=3.7",
]

[project.scripts]
octopus-mcp = "octopus_mcp.cli:main"

[project.urls]
Repository = "https://github.com/DanielChicot/octopus-mcp"
Issues = "https://github.com/DanielChicot/octopus-mcp/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/octopus_mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "live: tests that hit the real Octopus API (gated on OCTOPUS_API_KEY)",
]
```

- [ ] **Step 3: Create `src/octopus_mcp/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Create stub `src/octopus_mcp/cli.py`**

```python
def main() -> int:
    print("octopus-mcp (stub)")
    return 0
```

- [ ] **Step 5: Create empty `tests/__init__.py`**

(Empty file.)

- [ ] **Step 6: Install in editable mode and run tests**

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest tests/ -v
```

Expected: `test_version_is_set PASSED`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: scaffold octopus-mcp Python package"
```

---

### Task 2: Lint, type-check, pre-commit

**Files:**
- Create: `.pre-commit-config.yaml`
- Modify: `pyproject.toml` (add `[tool.ruff]`, `[tool.mypy]` sections)

- [ ] **Step 1: Append ruff and mypy config to `pyproject.toml`**

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "SIM", "RUF"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src", "tests"]
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["keyring.*", "tenacity.*"]
ignore_missing_imports = true
```

- [ ] **Step 2: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-keyring]
        files: ^(src|tests)/
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

- [ ] **Step 3: Install pre-commit and run on all files**

```bash
pre-commit install
pre-commit run --all-files
```

Expected: ruff/mypy/gitleaks pass on the (currently tiny) tree. Fix any style issues inline.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml
git commit -m "chore: add ruff, mypy strict, gitleaks via pre-commit"
```

---

### Task 3: CI, LICENSE, README skeleton, .env.example

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/dependabot.yml`
- Create: `LICENSE`
- Create: `README.md`
- Create: `.env.example`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CODE_OF_CONDUCT.md`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Set up Python
        run: uv python install ${{ matrix.python-version }}
      - name: Install
        run: uv pip install --system -e ".[dev]"
      - name: Lint
        run: ruff check . && ruff format --check .
      - name: Type-check
        run: mypy
      - name: Test
        run: pytest --cov=octopus_mcp --cov-report=term-missing
```

- [ ] **Step 2: Create `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

- [ ] **Step 3: Create `LICENSE` (MIT)**

```
MIT License

Copyright (c) 2026 Daniel Chicot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Create `.env.example`**

```
# Copy to .env and fill in. Never commit .env.
OCTOPUS_API_KEY=<your-octopus-api-key-here>
OCTOPUS_ACCOUNT_NUMBER=A-XXXXXXXX

# Optional — only needed for some Kraken queries.
# OCTOPUS_EMAIL=you@example.com
# OCTOPUS_PASSWORD=your-portal-password

# Optional — switch profiles for multi-account.
# OCTOPUS_PROFILE=default

# Optional — log level (DEBUG | INFO | WARNING | ERROR).
# OCTOPUS_MCP_LOG_LEVEL=INFO
```

- [ ] **Step 5: Create `README.md`** (skeleton — will flesh out in Task 30)

```markdown
# octopus-mcp

> Unofficial. Not affiliated with Octopus Energy. Uses the public REST API and the community-known Kraken GraphQL endpoint; the latter is unofficial and may break without notice.

An MCP server for analysing your Octopus Energy account with Claude.

**Status:** under construction. See `docs/superpowers/specs/` for design.

## License

MIT
```

- [ ] **Step 6: Create `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` (one-line stubs each)**

`CONTRIBUTING.md`:
```markdown
# Contributing

Issues and PRs welcome. Please run `pre-commit run --all-files` before pushing.

We use Conventional Commits and semver.
```

`SECURITY.md`:
```markdown
# Security Policy

Report vulnerabilities privately via GitHub Security Advisories on this repository.
Do not open public issues for security problems.
```

`CODE_OF_CONDUCT.md`:
```markdown
# Code of Conduct

This project follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
```

`CHANGELOG.md`:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
```

- [ ] **Step 7: Commit**

```bash
git add .github/ LICENSE README.md .env.example CONTRIBUTING.md SECURITY.md CODE_OF_CONDUCT.md CHANGELOG.md
git commit -m "chore: add CI, LICENSE, contributor docs, env template"
```

---

## Phase 1 — Octopus REST client

### Task 4: Exception hierarchy

**Files:**
- Create: `src/octopus_mcp/octopus/__init__.py`
- Create: `src/octopus_mcp/octopus/errors.py`
- Create: `tests/octopus/__init__.py`
- Create: `tests/octopus/test_errors.py`

- [ ] **Step 1: Write the failing test**

`tests/octopus/test_errors.py`:
```python
import pytest

from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    CacheError,
    ConfigError,
    DataError,
    NotFoundError,
    OctopusError,
    RateLimitError,
    ServiceError,
)


def test_all_errors_inherit_from_octopus_error():
    for cls in (
        AuthenticationError,
        AuthorizationError,
        RateLimitError,
        NotFoundError,
        ServiceError,
        DataError,
        CacheError,
        ConfigError,
    ):
        assert issubclass(cls, OctopusError)


def test_rate_limit_error_carries_retry_after():
    err = RateLimitError("rate limited", retry_after_seconds=30)
    assert err.retry_after_seconds == 30


def test_not_found_error_carries_resource_hint():
    err = NotFoundError("missing", resource="meter:1234")
    assert err.resource == "meter:1234"


def test_data_error_carries_truncated_excerpt():
    err = DataError("bad shape", raw_excerpt="x" * 5000)
    assert len(err.raw_excerpt) <= 1024


def test_octopus_error_can_be_raised_and_caught():
    with pytest.raises(OctopusError):
        raise AuthenticationError("nope")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/octopus/test_errors.py -v
```

Expected: ImportError / ModuleNotFoundError on `octopus_mcp.octopus.errors`.

- [ ] **Step 3: Create empty `src/octopus_mcp/octopus/__init__.py` and `tests/octopus/__init__.py`**

- [ ] **Step 4: Implement `src/octopus_mcp/octopus/errors.py`**

```python
"""Exception hierarchy for the Octopus client."""

from __future__ import annotations


class OctopusError(Exception):
    """Base class for all Octopus client errors."""


class AuthenticationError(OctopusError):
    """401 from upstream, or missing/bad credentials."""


class AuthorizationError(OctopusError):
    """403 from upstream."""


class RateLimitError(OctopusError):
    """429 from upstream."""

    def __init__(self, message: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class NotFoundError(OctopusError):
    """404 from upstream, or a missing resource we can name."""

    def __init__(self, message: str, *, resource: str | None = None) -> None:
        super().__init__(message)
        self.resource = resource


class ServiceError(OctopusError):
    """5xx from upstream."""


class DataError(OctopusError):
    """Unexpected response shape."""

    _MAX_EXCERPT = 1024

    def __init__(self, message: str, *, raw_excerpt: str | None = None) -> None:
        super().__init__(message)
        self.raw_excerpt = (raw_excerpt or "")[: self._MAX_EXCERPT]


class CacheError(OctopusError):
    """SQLite or repository failure."""


class ConfigError(OctopusError):
    """Missing or invalid configuration."""
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/octopus/test_errors.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/octopus_mcp/octopus/ tests/octopus/
git commit -m "feat(octopus): exception hierarchy"
```

---

### Task 5: Pydantic API response models

**Files:**
- Create: `src/octopus_mcp/octopus/models.py`
- Create: `tests/octopus/test_models.py`
- Create: `tests/octopus/fixtures/account_sample.json`
- Create: `tests/octopus/fixtures/consumption_sample.json`
- Create: `tests/octopus/fixtures/products_sample.json`
- Create: `tests/octopus/fixtures/unit_rates_sample.json`

- [ ] **Step 1: Create fixture files**

`tests/octopus/fixtures/account_sample.json`:
```json
{
  "number": "A-12345678",
  "properties": [
    {
      "id": 999,
      "moved_in_at": "2023-01-01T00:00:00Z",
      "moved_out_at": null,
      "address_line_1": "1 Example Road",
      "postcode": "EX1 1EX",
      "electricity_meter_points": [
        {
          "mpan": "1234567890123",
          "profile_class": 1,
          "consumption_standard": 3000,
          "meters": [
            {"serial_number": "ELEC001", "registers": [{"identifier": "1"}]}
          ],
          "agreements": [
            {
              "tariff_code": "E-1R-VAR-22-11-01-A",
              "valid_from": "2023-01-01T00:00:00Z",
              "valid_to": null
            }
          ]
        }
      ],
      "gas_meter_points": [
        {
          "mprn": "9876543210",
          "consumption_standard": 12000,
          "meters": [{"serial_number": "GAS001"}],
          "agreements": [
            {
              "tariff_code": "G-1R-VAR-22-11-01-A",
              "valid_from": "2023-01-01T00:00:00Z",
              "valid_to": null
            }
          ]
        }
      ]
    }
  ]
}
```

`tests/octopus/fixtures/consumption_sample.json`:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {"consumption": 0.234, "interval_start": "2026-04-25T00:00:00Z", "interval_end": "2026-04-25T00:30:00Z"},
    {"consumption": 0.187, "interval_start": "2026-04-25T00:30:00Z", "interval_end": "2026-04-25T01:00:00Z"}
  ]
}
```

`tests/octopus/fixtures/products_sample.json`:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "code": "VAR-22-11-01",
      "display_name": "Flexible Octopus",
      "full_name": "Flexible Octopus November 2022 v1",
      "description": "Default variable tariff",
      "is_variable": true,
      "is_green": true,
      "is_tracker": false,
      "is_prepay": false,
      "is_business": false,
      "brand": "OCTOPUS_ENERGY",
      "available_from": "2022-11-01T00:00:00Z",
      "available_to": null,
      "links": []
    }
  ]
}
```

`tests/octopus/fixtures/unit_rates_sample.json`:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {"value_exc_vat": 25.0, "value_inc_vat": 26.25, "valid_from": "2026-01-01T00:00:00Z", "valid_to": "2026-04-01T00:00:00Z"},
    {"value_exc_vat": 24.0, "value_inc_vat": 25.20, "valid_from": "2026-04-01T00:00:00Z", "valid_to": null}
  ]
}
```

- [ ] **Step 2: Write the failing test**

`tests/octopus/test_models.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from octopus_mcp.octopus.models import (
    Account,
    ConsumptionPage,
    Product,
    ProductPage,
    UnitRate,
    UnitRatePage,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_parses_account():
    acc = Account.model_validate(_load("account_sample.json"))
    assert acc.number == "A-12345678"
    assert len(acc.properties) == 1
    prop = acc.properties[0]
    assert prop.electricity_meter_points[0].mpan == "1234567890123"
    assert prop.gas_meter_points[0].mprn == "9876543210"
    agreement = prop.electricity_meter_points[0].agreements[0]
    assert agreement.valid_from == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert agreement.valid_to is None


def test_parses_consumption_page():
    page = ConsumptionPage.model_validate(_load("consumption_sample.json"))
    assert page.count == 2
    assert page.results[0].consumption == 0.234
    assert page.results[0].interval_start == datetime(2026, 4, 25, 0, 0, tzinfo=timezone.utc)


def test_parses_product_page():
    page = ProductPage.model_validate(_load("products_sample.json"))
    assert isinstance(page.results[0], Product)
    assert page.results[0].code == "VAR-22-11-01"
    assert page.results[0].is_variable is True


def test_parses_unit_rate_page():
    page = UnitRatePage.model_validate(_load("unit_rates_sample.json"))
    assert len(page.results) == 2
    rate: UnitRate = page.results[0]
    assert rate.value_inc_vat == 26.25
    assert rate.valid_to == datetime(2026, 4, 1, tzinfo=timezone.utc)


def test_models_reject_unknown_extra_fields_loosely():
    # Octopus may add fields; we should not break.
    extra = {"count": 0, "next": None, "previous": None, "results": [], "extra_field": "ignore me"}
    page = ConsumptionPage.model_validate(extra)
    assert page.count == 0
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/octopus/test_models.py -v
```

Expected: ImportError on `octopus_mcp.octopus.models`.

- [ ] **Step 4: Implement `src/octopus_mcp/octopus/models.py`**

```python
"""Pydantic models for Octopus REST API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

_BASE_CONFIG = ConfigDict(extra="ignore", populate_by_name=True)

T = TypeVar("T")


class _Base(BaseModel):
    model_config = _BASE_CONFIG


class Page(_Base, Generic[T]):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[T]


class Agreement(_Base):
    tariff_code: str
    valid_from: datetime
    valid_to: datetime | None = None


class MeterRegister(_Base):
    identifier: str | None = None


class Meter(_Base):
    serial_number: str
    registers: list[MeterRegister] = Field(default_factory=list)


class ElectricityMeterPoint(_Base):
    mpan: str
    profile_class: int | None = None
    consumption_standard: int | None = None
    is_export: bool = False
    meters: list[Meter] = Field(default_factory=list)
    agreements: list[Agreement] = Field(default_factory=list)


class GasMeterPoint(_Base):
    mprn: str
    consumption_standard: int | None = None
    meters: list[Meter] = Field(default_factory=list)
    agreements: list[Agreement] = Field(default_factory=list)


class Property(_Base):
    id: int
    moved_in_at: datetime | None = None
    moved_out_at: datetime | None = None
    address_line_1: str | None = None
    postcode: str | None = None
    electricity_meter_points: list[ElectricityMeterPoint] = Field(default_factory=list)
    gas_meter_points: list[GasMeterPoint] = Field(default_factory=list)


class Account(_Base):
    number: str
    properties: list[Property] = Field(default_factory=list)


class ConsumptionRow(_Base):
    consumption: float
    interval_start: datetime
    interval_end: datetime


class ConsumptionPage(Page[ConsumptionRow]):
    pass


class Product(_Base):
    code: str
    display_name: str
    full_name: str | None = None
    description: str | None = None
    is_variable: bool = False
    is_green: bool = False
    is_tracker: bool = False
    is_prepay: bool = False
    is_business: bool = False
    brand: str | None = None
    available_from: datetime | None = None
    available_to: datetime | None = None


class ProductPage(Page[Product]):
    pass


class UnitRate(_Base):
    value_exc_vat: float
    value_inc_vat: float
    valid_from: datetime
    valid_to: datetime | None = None


class UnitRatePage(Page[UnitRate]):
    pass


class StandingCharge(_Base):
    value_exc_vat: float
    value_inc_vat: float
    valid_from: datetime
    valid_to: datetime | None = None


class StandingChargePage(Page[StandingCharge]):
    pass
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/octopus/test_models.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/octopus_mcp/octopus/models.py tests/octopus/test_models.py tests/octopus/fixtures/
git commit -m "feat(octopus): pydantic models for REST responses"
```

---

### Task 6: Credential resolution (`auth.py`)

**Files:**
- Create: `src/octopus_mcp/octopus/auth.py`
- Create: `tests/octopus/test_auth.py`

- [ ] **Step 1: Write the failing test**

`tests/octopus/test_auth.py`:
```python
import os
from unittest.mock import patch

import pytest

from octopus_mcp.octopus.auth import OctopusCredentials, resolve_credentials
from octopus_mcp.octopus.errors import ConfigError


def test_env_vars_take_precedence(monkeypatch):
    monkeypatch.setenv("OCTOPUS_API_KEY", "sk_test_env")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-ENV")
    creds = resolve_credentials()
    assert creds.api_key == "sk_test_env"
    assert creds.account_number == "A-ENV"


def test_optional_email_and_password_loaded(monkeypatch):
    monkeypatch.setenv("OCTOPUS_API_KEY", "k")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-1")
    monkeypatch.setenv("OCTOPUS_EMAIL", "x@y.z")
    monkeypatch.setenv("OCTOPUS_PASSWORD", "secret")
    creds = resolve_credentials()
    assert creds.email == "x@y.z"
    assert creds.password == "secret"


def test_missing_creds_raises_config_error(monkeypatch):
    for v in ("OCTOPUS_API_KEY", "OCTOPUS_ACCOUNT_NUMBER", "OCTOPUS_EMAIL", "OCTOPUS_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    with patch("octopus_mcp.octopus.auth._keyring_get", return_value=None):
        with pytest.raises(ConfigError) as exc:
            resolve_credentials()
        assert "octopus-mcp configure" in str(exc.value)


def test_keyring_used_when_env_missing(monkeypatch):
    monkeypatch.delenv("OCTOPUS_API_KEY", raising=False)
    monkeypatch.delenv("OCTOPUS_ACCOUNT_NUMBER", raising=False)

    def fake_get(profile: str, key: str) -> str | None:
        return {"api_key": "sk_test_kr", "account_number": "A-KR"}.get(key)

    with patch("octopus_mcp.octopus.auth._keyring_get", side_effect=fake_get):
        creds = resolve_credentials()
        assert creds.api_key == "sk_test_kr"
        assert creds.account_number == "A-KR"


def test_repr_redacts_secrets():
    c = OctopusCredentials(
        api_key="sk_secret",
        account_number="A-1",
        email="x@y.z",
        password="hunter2",
        profile="default",
    )
    rendered = repr(c)
    assert "sk_secret" not in rendered
    assert "hunter2" not in rendered
    assert "A-1" not in rendered
    assert "default" in rendered  # non-secret OK
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/octopus/test_auth.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/octopus/auth.py`**

```python
"""Credential resolution: env > .env > keyring > config.toml > error."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

from octopus_mcp.octopus.errors import ConfigError

_KEYRING_SERVICE = "octopus-mcp"
_ENV_LOADED = False


def _ensure_dotenv_loaded() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    found = find_dotenv(usecwd=True)
    if found:
        load_dotenv(found, override=False)
    _ENV_LOADED = True


def _keyring_get(profile: str, key: str) -> str | None:
    """Indirection so tests can patch."""
    try:
        import keyring
    except ImportError:
        return None
    return keyring.get_password(f"{_KEYRING_SERVICE}:{profile}", key)


@dataclass(frozen=True)
class OctopusCredentials:
    api_key: str
    account_number: str
    profile: str = "default"
    email: str | None = None
    password: str | None = None

    def __repr__(self) -> str:  # never leak secrets in logs
        return f"OctopusCredentials(profile={self.profile!r}, api_key=***, account=***)"


def _read(profile: str, key: str, env_var: str) -> str | None:
    val = os.environ.get(env_var)
    if val:
        return val
    return _keyring_get(profile, key)


def resolve_credentials(profile: str | None = None) -> OctopusCredentials:
    _ensure_dotenv_loaded()
    profile = profile or os.environ.get("OCTOPUS_PROFILE", "default")

    api_key = _read(profile, "api_key", "OCTOPUS_API_KEY")
    account_number = _read(profile, "account_number", "OCTOPUS_ACCOUNT_NUMBER")
    email = _read(profile, "email", "OCTOPUS_EMAIL")
    password = _read(profile, "password", "OCTOPUS_PASSWORD")

    missing = [name for name, val in [("OCTOPUS_API_KEY", api_key), ("OCTOPUS_ACCOUNT_NUMBER", account_number)] if not val]
    if missing:
        raise ConfigError(
            f"Missing required credentials: {', '.join(missing)}. "
            "Run: octopus-mcp configure"
        )

    return OctopusCredentials(
        api_key=api_key,  # type: ignore[arg-type]
        account_number=account_number,  # type: ignore[arg-type]
        profile=profile,
        email=email,
        password=password,
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/octopus/test_auth.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/octopus/auth.py tests/octopus/test_auth.py
git commit -m "feat(octopus): credential resolution with env > .env > keyring chain"
```

---

### Task 7: REST client foundation with retry & rate-limit

**Files:**
- Create: `src/octopus_mcp/octopus/rest.py`
- Create: `tests/octopus/test_rest_transport.py`

- [ ] **Step 1: Write the failing test**

`tests/octopus/test_rest_transport.py`:
```python
import httpx
import pytest

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceError,
)
from octopus_mcp.octopus.rest import OctopusRestClient


def _creds() -> OctopusCredentials:
    return OctopusCredentials(api_key="sk_test", account_number="A-1")


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return OctopusRestClient(_creds(), http_client=http)


@pytest.mark.asyncio
async def test_get_uses_basic_auth():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    async with _make_client(handler) as client:
        await client._get_json("/v1/products/")  # noqa: SLF001
    assert captured["auth"].startswith("Basic ")


@pytest.mark.asyncio
async def test_401_raises_authentication_error():
    def handler(_):
        return httpx.Response(401, json={"detail": "Invalid token"})

    async with _make_client(handler) as client:
        with pytest.raises(AuthenticationError):
            await client._get_json("/v1/products/")  # noqa: SLF001


@pytest.mark.asyncio
async def test_403_raises_authorization_error():
    async with _make_client(lambda _: httpx.Response(403)) as client:
        with pytest.raises(AuthorizationError):
            await client._get_json("/v1/x")  # noqa: SLF001


@pytest.mark.asyncio
async def test_404_raises_not_found_error():
    async with _make_client(lambda _: httpx.Response(404)) as client:
        with pytest.raises(NotFoundError):
            await client._get_json("/v1/x")  # noqa: SLF001


@pytest.mark.asyncio
async def test_429_raises_rate_limit_with_retry_after():
    async with _make_client(
        lambda _: httpx.Response(429, headers={"Retry-After": "12"})
    ) as client:
        with pytest.raises(RateLimitError) as exc:
            await client._get_json("/v1/x")  # noqa: SLF001
        assert exc.value.retry_after_seconds == 12


@pytest.mark.asyncio
async def test_500_retries_then_raises_service_error():
    calls = {"n": 0}

    def handler(_):
        calls["n"] += 1
        return httpx.Response(500)

    async with _make_client(handler) as client:
        with pytest.raises(ServiceError):
            await client._get_json("/v1/x")  # noqa: SLF001
    assert calls["n"] == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_500_then_200_recovers():
    calls = {"n": 0}

    def handler(_):
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    async with _make_client(handler) as client:
        out = await client._get_json("/v1/x")  # noqa: SLF001
    assert out == {"ok": True}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/octopus/test_rest_transport.py -v
```

Expected: ImportError on `octopus_mcp.octopus.rest`.

- [ ] **Step 3: Implement `src/octopus_mcp/octopus/rest.py`**

```python
"""Async HTTP client for the Octopus public REST API."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ServiceError,
)

_BASE_URL = "https://api.octopus.energy"
_log = logging.getLogger(__name__)


class _RetryableHTTPError(Exception):
    pass


class OctopusRestClient:
    """Thin wrapper around httpx with auth, retry, and error mapping."""

    def __init__(
        self,
        credentials: OctopusCredentials,
        *,
        http_client: httpx.AsyncClient | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._creds = credentials
        self._max_attempts = max_attempts
        token = base64.b64encode(f"{credentials.api_key}:".encode()).decode()
        self._auth_header = {"Authorization": f"Basic {token}"}
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(30.0),
        )

    async def __aenter__(self) -> "OctopusRestClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        async def _attempt() -> dict[str, Any]:
            resp = await self._http.get(path, params=params, headers=self._auth_header)
            return self._handle(resp)

        try:
            async for attempt in AsyncRetrying(
                reraise=True,
                stop=stop_after_attempt(self._max_attempts),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
                retry=retry_if_exception_type((_RetryableHTTPError, httpx.TransportError)),
            ):
                with attempt:
                    return await _attempt()
        except RetryError as e:  # pragma: no cover - tenacity reraises last exc
            raise ServiceError("retries exhausted") from e
        raise ServiceError("unreachable")

    @staticmethod
    def _handle(resp: httpx.Response) -> dict[str, Any]:
        if 200 <= resp.status_code < 300:
            return resp.json()
        if resp.status_code == 401:
            raise AuthenticationError("Octopus API rejected credentials (401)")
        if resp.status_code == 403:
            raise AuthorizationError("Octopus API forbade request (403)")
        if resp.status_code == 404:
            raise NotFoundError(f"Resource not found: {resp.request.url.path}")
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Octopus API rate-limited",
                retry_after_seconds=int(ra) if ra and ra.isdigit() else None,
            )
        if 500 <= resp.status_code < 600:
            raise _RetryableHTTPError(f"upstream {resp.status_code}")
        raise ServiceError(f"Unexpected status {resp.status_code}")
```

Note: when tenacity exhausts on `_RetryableHTTPError` it will reraise that exception type. We map it to `ServiceError` here to surface a stable public type.

Actually fix: convert `_RetryableHTTPError` into `ServiceError` outside the retry loop. Adjust:

```python
        try:
            async for attempt in AsyncRetrying(...):
                with attempt:
                    return await _attempt()
        except _RetryableHTTPError as e:
            raise ServiceError(str(e)) from e
        except RetryError as e:  # pragma: no cover
            raise ServiceError("retries exhausted") from e
        raise ServiceError("unreachable")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/octopus/test_rest_transport.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/octopus/rest.py tests/octopus/test_rest_transport.py
git commit -m "feat(octopus): async REST client with auth, retry, and error mapping"
```

---

### Task 8: REST endpoint methods

**Files:**
- Modify: `src/octopus_mcp/octopus/rest.py` (add typed methods)
- Create: `tests/octopus/test_rest_endpoints.py`

- [ ] **Step 1: Write the failing test**

`tests/octopus/test_rest_endpoints.py`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.rest import OctopusRestClient

FIXTURES = Path(__file__).parent / "fixtures"


def _resp(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return OctopusRestClient(OctopusCredentials(api_key="k", account_number="A-1"), http_client=http)


@pytest.mark.asyncio
async def test_get_account_returns_typed_account():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/accounts/A-1/"
        return httpx.Response(200, json=_resp("account_sample.json"))

    async with _client(handler) as c:
        account = await c.get_account()
    assert account.number == "A-12345678"


@pytest.mark.asyncio
async def test_get_consumption_passes_period_params_and_pages():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=_resp("consumption_sample.json"))

    async with _client(handler) as c:
        rows = await c.get_electricity_consumption(
            mpan="1234567890123",
            serial="ELEC001",
            period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
            period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
        )
    assert len(rows) == 2
    assert captured["params"]["period_from"] == "2026-04-25T00:00:00+00:00"
    assert captured["params"]["page_size"] == "25000"


@pytest.mark.asyncio
async def test_get_consumption_follows_next_pages():
    pages = [
        {
            "count": 4,
            "next": "https://api.octopus.energy/v1/electricity-meter-points/1/meters/S/consumption/?page=2",
            "previous": None,
            "results": [
                {"consumption": 0.1, "interval_start": "2026-04-25T00:00:00Z", "interval_end": "2026-04-25T00:30:00Z"},
                {"consumption": 0.2, "interval_start": "2026-04-25T00:30:00Z", "interval_end": "2026-04-25T01:00:00Z"},
            ],
        },
        {
            "count": 4,
            "next": None,
            "previous": None,
            "results": [
                {"consumption": 0.3, "interval_start": "2026-04-25T01:00:00Z", "interval_end": "2026-04-25T01:30:00Z"},
                {"consumption": 0.4, "interval_start": "2026-04-25T01:30:00Z", "interval_end": "2026-04-25T02:00:00Z"},
            ],
        },
    ]
    seen = {"i": 0}

    def handler(_):
        body = pages[seen["i"]]
        seen["i"] += 1
        return httpx.Response(200, json=body)

    async with _client(handler) as c:
        rows = await c.get_electricity_consumption(mpan="1", serial="S")
    assert len(rows) == 4
    assert seen["i"] == 2


@pytest.mark.asyncio
async def test_list_products_unauthenticated_path():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json=_resp("products_sample.json"))

    async with _client(handler) as c:
        products = await c.list_products()
    assert captured["path"] == "/v1/products/"
    assert products[0].code == "VAR-22-11-01"


@pytest.mark.asyncio
async def test_get_unit_rates():
    def handler(_):
        return httpx.Response(200, json=_resp("unit_rates_sample.json"))

    async with _client(handler) as c:
        rates = await c.get_electricity_unit_rates(
            product_code="VAR-22-11-01",
            tariff_code="E-1R-VAR-22-11-01-A",
        )
    assert len(rates) == 2
    assert rates[0].value_inc_vat == 26.25
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/octopus/test_rest_endpoints.py -v
```

Expected: AttributeError — methods not defined.

- [ ] **Step 3: Add typed endpoint methods to `src/octopus_mcp/octopus/rest.py`**

Append to the `OctopusRestClient` class:

```python
    # ---- account ----

    async def get_account(self, account_number: str | None = None):
        from octopus_mcp.octopus.models import Account

        number = account_number or self._creds.account_number
        data = await self._get_json(f"/v1/accounts/{number}/")
        return Account.model_validate(data)

    # ---- consumption ----

    async def get_electricity_consumption(
        self,
        mpan: str,
        serial: str,
        *,
        period_from: "datetime | None" = None,
        period_to: "datetime | None" = None,
    ):
        return await self._consumption(
            f"/v1/electricity-meter-points/{mpan}/meters/{serial}/consumption/",
            period_from,
            period_to,
        )

    async def get_gas_consumption(
        self,
        mprn: str,
        serial: str,
        *,
        period_from: "datetime | None" = None,
        period_to: "datetime | None" = None,
    ):
        return await self._consumption(
            f"/v1/gas-meter-points/{mprn}/meters/{serial}/consumption/",
            period_from,
            period_to,
        )

    async def _consumption(self, path: str, period_from, period_to):
        from octopus_mcp.octopus.models import ConsumptionPage, ConsumptionRow

        params: dict[str, Any] = {"page_size": 25000, "order_by": "period"}
        if period_from is not None:
            params["period_from"] = period_from.isoformat()
        if period_to is not None:
            params["period_to"] = period_to.isoformat()

        rows: list[ConsumptionRow] = []
        next_url: str | None = path
        next_params: dict[str, Any] | None = params
        while next_url is not None:
            data = await self._get_json(next_url, params=next_params)
            page = ConsumptionPage.model_validate(data)
            rows.extend(page.results)
            next_url = self._strip_base(page.next)
            next_params = None  # next URL already includes params
        return rows

    @staticmethod
    def _strip_base(url: str | None) -> str | None:
        if url is None:
            return None
        if url.startswith(_BASE_URL):
            return url[len(_BASE_URL) :]
        return url

    # ---- products ----

    async def list_products(self):
        from octopus_mcp.octopus.models import ProductPage

        data = await self._get_json("/v1/products/")
        return ProductPage.model_validate(data).results

    async def get_product(self, code: str) -> dict[str, Any]:
        return await self._get_json(f"/v1/products/{code}/")

    # ---- tariff rates ----

    async def get_electricity_unit_rates(self, product_code: str, tariff_code: str):
        from octopus_mcp.octopus.models import UnitRatePage

        path = f"/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"
        data = await self._get_json(path, params={"page_size": 1500})
        return UnitRatePage.model_validate(data).results

    async def get_electricity_standing_charges(self, product_code: str, tariff_code: str):
        from octopus_mcp.octopus.models import StandingChargePage

        path = f"/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standing-charges/"
        data = await self._get_json(path, params={"page_size": 1500})
        return StandingChargePage.model_validate(data).results

    async def get_gas_unit_rates(self, product_code: str, tariff_code: str):
        from octopus_mcp.octopus.models import UnitRatePage

        path = f"/v1/products/{product_code}/gas-tariffs/{tariff_code}/standard-unit-rates/"
        data = await self._get_json(path, params={"page_size": 1500})
        return UnitRatePage.model_validate(data).results

    async def get_gas_standing_charges(self, product_code: str, tariff_code: str):
        from octopus_mcp.octopus.models import StandingChargePage

        path = f"/v1/products/{product_code}/gas-tariffs/{tariff_code}/standing-charges/"
        data = await self._get_json(path, params={"page_size": 1500})
        return StandingChargePage.model_validate(data).results
```

Add `from datetime import datetime` near the top.

- [ ] **Step 4: Run tests**

```bash
pytest tests/octopus/ -v
```

Expected: all REST tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/octopus/rest.py tests/octopus/test_rest_endpoints.py
git commit -m "feat(octopus): typed REST endpoint methods (account, consumption, products, rates)"
```

---

## Phase 2 — Cache (SQLite)

### Task 9: Schema + migration runner

**Files:**
- Create: `src/octopus_mcp/cache/__init__.py`
- Create: `src/octopus_mcp/cache/migrations/__init__.py`
- Create: `src/octopus_mcp/cache/migrations/001_init.sql`
- Create: `src/octopus_mcp/cache/db.py`
- Create: `tests/cache/__init__.py`
- Create: `tests/cache/test_db.py`

- [ ] **Step 1: Write the failing test**

`tests/cache/test_db.py`:
```python
import sqlite3

from octopus_mcp.cache.db import open_db, run_migrations


def test_open_db_in_memory_runs_migrations():
    conn = open_db(":memory:")
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    expected = {
        "consumption",
        "unit_rates",
        "standing_charges",
        "meters",
        "tariff_assignments",
        "products",
        "saving_sessions",
        "octoplus_events",
        "sync_state",
    }
    assert expected.issubset(tables)


def test_user_version_advances_after_migration():
    conn = open_db(":memory:")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version >= 1


def test_running_migrations_twice_is_idempotent():
    conn = open_db(":memory:")
    run_migrations(conn)  # second invocation
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert version >= 1


def test_wal_mode_enabled(tmp_path):
    db_path = tmp_path / "test.db"
    conn = open_db(str(db_path))
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/cache/test_db.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create empty `__init__.py` files**

`src/octopus_mcp/cache/__init__.py`, `src/octopus_mcp/cache/migrations/__init__.py`, `tests/cache/__init__.py` (empty).

- [ ] **Step 4: Create `src/octopus_mcp/cache/migrations/001_init.sql`**

```sql
-- 001_init: full v1 schema.

CREATE TABLE consumption (
  fuel             TEXT NOT NULL,
  mpan_or_mprn     TEXT NOT NULL,
  serial_number    TEXT NOT NULL,
  interval_start   TEXT NOT NULL,
  interval_end     TEXT NOT NULL,
  consumption_kwh  REAL NOT NULL,
  PRIMARY KEY (fuel, mpan_or_mprn, serial_number, interval_start)
);
CREATE INDEX idx_consumption_range ON consumption (fuel, interval_start);

CREATE TABLE unit_rates (
  tariff_code   TEXT NOT NULL,
  fuel          TEXT NOT NULL,
  valid_from    TEXT NOT NULL,
  valid_to      TEXT,
  value_inc_vat REAL NOT NULL,
  value_exc_vat REAL NOT NULL,
  PRIMARY KEY (tariff_code, valid_from)
);

CREATE TABLE standing_charges (
  tariff_code   TEXT NOT NULL,
  fuel          TEXT NOT NULL,
  valid_from    TEXT NOT NULL,
  valid_to      TEXT,
  value_inc_vat REAL NOT NULL,
  value_exc_vat REAL NOT NULL,
  PRIMARY KEY (tariff_code, valid_from)
);

CREATE TABLE meters (
  account_number TEXT NOT NULL,
  fuel           TEXT NOT NULL,
  mpan_or_mprn   TEXT NOT NULL,
  serial_number  TEXT NOT NULL,
  is_export      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (account_number, fuel, mpan_or_mprn, serial_number)
);

CREATE TABLE tariff_assignments (
  account_number TEXT NOT NULL,
  fuel           TEXT NOT NULL,
  product_code   TEXT NOT NULL,
  tariff_code    TEXT NOT NULL,
  valid_from     TEXT NOT NULL,
  valid_to       TEXT,
  PRIMARY KEY (account_number, fuel, valid_from)
);

CREATE TABLE products (
  code         TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  brand        TEXT,
  payload_json TEXT NOT NULL,
  fetched_at   TEXT NOT NULL
);

CREATE TABLE saving_sessions (
  id              TEXT PRIMARY KEY,
  code            TEXT,
  starts_at       TEXT NOT NULL,
  ends_at         TEXT NOT NULL,
  points_awarded  INTEGER,
  kwh_saved       REAL,
  joined          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE octoplus_events (
  id            TEXT PRIMARY KEY,
  event_type    TEXT NOT NULL,
  points        INTEGER,
  occurred_at   TEXT NOT NULL,
  payload_json  TEXT NOT NULL
);

CREATE TABLE sync_state (
  resource        TEXT PRIMARY KEY,
  last_synced_at  TEXT NOT NULL,
  ttl_seconds     INTEGER
);
```

- [ ] **Step 5: Implement `src/octopus_mcp/cache/db.py`**

```python
"""SQLite connection + migration runner."""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

from octopus_mcp.cache import migrations as migrations_pkg

_MIGRATIONS_DIR = "octopus_mcp.cache.migrations"


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn)
    return conn


def _list_migrations() -> list[tuple[int, str]]:
    files = []
    for entry in resources.files(migrations_pkg).iterdir():
        name = entry.name
        if name.endswith(".sql"):
            num = int(name.split("_", 1)[0])
            files.append((num, entry.read_text()))
    files.sort()
    return files


def run_migrations(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version, sql in _list_migrations():
        if version <= current:
            continue
        conn.executescript(sql)
        conn.execute(f"PRAGMA user_version = {version}")
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/cache/test_db.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/octopus_mcp/cache/ tests/cache/
git commit -m "feat(cache): SQLite schema and migration runner"
```

---

### Task 10: Consumption repository + watermark

**Files:**
- Create: `src/octopus_mcp/cache/consumption.py`
- Create: `tests/cache/test_consumption.py`

- [ ] **Step 1: Write the failing test**

`tests/cache/test_consumption.py`:
```python
from datetime import datetime, timezone

import pytest

from octopus_mcp.cache.consumption import (
    ConsumptionRepo,
    ConsumptionRowIn,
)
from octopus_mcp.cache.db import open_db


@pytest.fixture
def repo():
    return ConsumptionRepo(open_db(":memory:"))


def _row(start: str, kwh: float) -> ConsumptionRowIn:
    return ConsumptionRowIn(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        interval_start=datetime.fromisoformat(start.replace("Z", "+00:00")),
        interval_end=datetime.fromisoformat(start.replace("Z", "+00:00")),
        consumption_kwh=kwh,
    )


def test_upsert_and_read_back(repo: ConsumptionRepo):
    repo.upsert([_row("2026-04-25T00:00:00Z", 0.5), _row("2026-04-25T00:30:00Z", 0.3)])
    rows = repo.get_range(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert [r.consumption_kwh for r in rows] == [0.5, 0.3]


def test_upsert_is_idempotent(repo: ConsumptionRepo):
    r = _row("2026-04-25T00:00:00Z", 0.5)
    repo.upsert([r, r])
    rows = repo.get_range(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert len(rows) == 1


def test_watermark_returns_max_interval_start(repo: ConsumptionRepo):
    repo.upsert([_row("2026-04-25T00:00:00Z", 0.5), _row("2026-04-26T03:00:00Z", 0.7)])
    wm = repo.latest_interval_start(fuel="electricity", mpan_or_mprn="123", serial_number="S")
    assert wm == datetime(2026, 4, 26, 3, 0, tzinfo=timezone.utc)


def test_watermark_none_when_empty(repo: ConsumptionRepo):
    assert repo.latest_interval_start(fuel="electricity", mpan_or_mprn="123", serial_number="S") is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/cache/test_consumption.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/cache/consumption.py`**

```python
"""Consumption rows: read, upsert, watermark."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Literal


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ConsumptionRowIn:
    fuel: Literal["electricity", "gas"]
    mpan_or_mprn: str
    serial_number: str
    interval_start: datetime
    interval_end: datetime
    consumption_kwh: float


@dataclass(frozen=True)
class ConsumptionRow:
    fuel: str
    mpan_or_mprn: str
    serial_number: str
    interval_start: datetime
    interval_end: datetime
    consumption_kwh: float


class ConsumptionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, rows: Iterable[ConsumptionRowIn]) -> int:
        cur = self._conn.executemany(
            """
            INSERT INTO consumption (fuel, mpan_or_mprn, serial_number,
                                     interval_start, interval_end, consumption_kwh)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(fuel, mpan_or_mprn, serial_number, interval_start)
            DO UPDATE SET consumption_kwh = excluded.consumption_kwh,
                          interval_end = excluded.interval_end
            """,
            [
                (
                    r.fuel,
                    r.mpan_or_mprn,
                    r.serial_number,
                    _iso(r.interval_start),
                    _iso(r.interval_end),
                    r.consumption_kwh,
                )
                for r in rows
            ],
        )
        return cur.rowcount

    def get_range(
        self,
        *,
        fuel: str,
        mpan_or_mprn: str,
        serial_number: str,
        period_from: datetime,
        period_to: datetime,
    ) -> list[ConsumptionRow]:
        rows = self._conn.execute(
            """
            SELECT fuel, mpan_or_mprn, serial_number,
                   interval_start, interval_end, consumption_kwh
              FROM consumption
             WHERE fuel = ? AND mpan_or_mprn = ? AND serial_number = ?
               AND interval_start >= ? AND interval_start < ?
             ORDER BY interval_start
            """,
            (fuel, mpan_or_mprn, serial_number, _iso(period_from), _iso(period_to)),
        ).fetchall()
        return [
            ConsumptionRow(
                fuel=r["fuel"],
                mpan_or_mprn=r["mpan_or_mprn"],
                serial_number=r["serial_number"],
                interval_start=_parse(r["interval_start"]),
                interval_end=_parse(r["interval_end"]),
                consumption_kwh=r["consumption_kwh"],
            )
            for r in rows
        ]

    def latest_interval_start(
        self, *, fuel: str, mpan_or_mprn: str, serial_number: str
    ) -> datetime | None:
        row = self._conn.execute(
            """
            SELECT MAX(interval_start) AS m
              FROM consumption
             WHERE fuel = ? AND mpan_or_mprn = ? AND serial_number = ?
            """,
            (fuel, mpan_or_mprn, serial_number),
        ).fetchone()
        return _parse(row["m"]) if row and row["m"] else None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/cache/test_consumption.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/cache/consumption.py tests/cache/test_consumption.py
git commit -m "feat(cache): consumption repo with idempotent upsert and watermark"
```

---

### Task 11: Repositories for rates, meters, products, sync state

**Files:**
- Create: `src/octopus_mcp/cache/rates.py`
- Create: `src/octopus_mcp/cache/meters.py`
- Create: `src/octopus_mcp/cache/products.py`
- Create: `src/octopus_mcp/cache/sync_state.py`
- Create: `tests/cache/test_rates.py`
- Create: `tests/cache/test_meters.py`
- Create: `tests/cache/test_products.py`
- Create: `tests/cache/test_sync_state.py`

- [ ] **Step 1: Write `tests/cache/test_rates.py`**

```python
from datetime import datetime, timezone

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.rates import RateRow, RatesRepo


def test_upsert_and_read_unit_rates():
    repo = RatesRepo(open_db(":memory:"))
    repo.upsert_unit_rates(
        tariff_code="E-1R-VAR-22-11-01-A",
        fuel="electricity",
        rows=[
            RateRow(valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc), valid_to=datetime(2026, 4, 1, tzinfo=timezone.utc), value_inc_vat=26.25, value_exc_vat=25.0),
            RateRow(valid_from=datetime(2026, 4, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=25.20, value_exc_vat=24.0),
        ],
    )
    rows = repo.get_unit_rates("E-1R-VAR-22-11-01-A")
    assert len(rows) == 2
    assert rows[0].value_inc_vat == 26.25


def test_upsert_standing_charges():
    repo = RatesRepo(open_db(":memory:"))
    repo.upsert_standing_charges(
        tariff_code="E-1R-VAR-22-11-01-A",
        fuel="electricity",
        rows=[RateRow(valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=50.0, value_exc_vat=47.62)],
    )
    rows = repo.get_standing_charges("E-1R-VAR-22-11-01-A")
    assert rows[0].value_inc_vat == 50.0
```

- [ ] **Step 2: Write `tests/cache/test_meters.py`**

```python
from datetime import datetime, timezone

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.meters import MeterRow, MetersRepo, TariffAssignmentRow


def test_upsert_and_list_meters():
    repo = MetersRepo(open_db(":memory:"))
    repo.upsert_meters(
        [
            MeterRow(account_number="A-1", fuel="electricity", mpan_or_mprn="111", serial_number="ELEC", is_export=False),
            MeterRow(account_number="A-1", fuel="gas", mpan_or_mprn="999", serial_number="GAS", is_export=False),
        ]
    )
    elec = repo.list_meters_for_account("A-1", fuel="electricity")
    assert len(elec) == 1 and elec[0].mpan_or_mprn == "111"


def test_upsert_and_query_tariff_assignments():
    repo = MetersRepo(open_db(":memory:"))
    repo.upsert_tariff_assignments(
        [
            TariffAssignmentRow(
                account_number="A-1",
                fuel="electricity",
                product_code="VAR-22-11-01",
                tariff_code="E-1R-VAR-22-11-01-A",
                valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
                valid_to=None,
            )
        ]
    )
    current = repo.current_tariff_assignment(account_number="A-1", fuel="electricity", at=datetime(2026, 4, 25, tzinfo=timezone.utc))
    assert current is not None and current.tariff_code == "E-1R-VAR-22-11-01-A"
```

- [ ] **Step 3: Write `tests/cache/test_products.py`**

```python
import json
from datetime import datetime, timezone

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.products import ProductRow, ProductsRepo


def test_upsert_and_list_products():
    repo = ProductsRepo(open_db(":memory:"))
    repo.upsert(
        [
            ProductRow(code="VAR-22-11-01", display_name="Flexible", brand="OE", payload={"foo": "bar"}, fetched_at=datetime(2026, 4, 25, tzinfo=timezone.utc)),
        ]
    )
    products = repo.list_all()
    assert products[0].code == "VAR-22-11-01"
    assert products[0].payload == {"foo": "bar"}


def test_get_by_code_returns_none_when_missing():
    repo = ProductsRepo(open_db(":memory:"))
    assert repo.get_by_code("MISSING") is None
```

- [ ] **Step 4: Write `tests/cache/test_sync_state.py`**

```python
from datetime import datetime, timedelta, timezone

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.sync_state import SyncStateRepo


def test_set_and_get_watermark():
    repo = SyncStateRepo(open_db(":memory:"))
    now = datetime(2026, 4, 25, tzinfo=timezone.utc)
    repo.touch("products", at=now, ttl_seconds=86400)
    assert repo.last_synced("products") == now


def test_is_fresh_within_ttl():
    repo = SyncStateRepo(open_db(":memory:"))
    now = datetime(2026, 4, 25, tzinfo=timezone.utc)
    repo.touch("products", at=now, ttl_seconds=3600)
    assert repo.is_fresh("products", now=now + timedelta(minutes=30)) is True
    assert repo.is_fresh("products", now=now + timedelta(hours=2)) is False


def test_is_fresh_returns_false_when_unknown():
    repo = SyncStateRepo(open_db(":memory:"))
    assert repo.is_fresh("never-synced", now=datetime.now(timezone.utc)) is False
```

- [ ] **Step 5: Run failing tests**

```bash
pytest tests/cache/test_rates.py tests/cache/test_meters.py tests/cache/test_products.py tests/cache/test_sync_state.py -v
```

Expected: ImportError on each.

- [ ] **Step 6: Implement `src/octopus_mcp/cache/rates.py`**

```python
"""Tariff unit-rate and standing-charge repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


@dataclass(frozen=True)
class RateRow:
    valid_from: datetime
    valid_to: datetime | None
    value_inc_vat: float
    value_exc_vat: float


class RatesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_unit_rates(self, *, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        self._upsert("unit_rates", tariff_code, fuel, rows)

    def upsert_standing_charges(self, *, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        self._upsert("standing_charges", tariff_code, fuel, rows)

    def _upsert(self, table: str, tariff_code: str, fuel: str, rows: list[RateRow]) -> None:
        self._conn.executemany(
            f"""
            INSERT INTO {table} (tariff_code, fuel, valid_from, valid_to, value_inc_vat, value_exc_vat)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tariff_code, valid_from)
            DO UPDATE SET valid_to=excluded.valid_to,
                          value_inc_vat=excluded.value_inc_vat,
                          value_exc_vat=excluded.value_exc_vat,
                          fuel=excluded.fuel
            """,
            [(tariff_code, fuel, _iso(r.valid_from), _iso(r.valid_to), r.value_inc_vat, r.value_exc_vat) for r in rows],
        )

    def get_unit_rates(self, tariff_code: str) -> list[RateRow]:
        return self._select("unit_rates", tariff_code)

    def get_standing_charges(self, tariff_code: str) -> list[RateRow]:
        return self._select("standing_charges", tariff_code)

    def _select(self, table: str, tariff_code: str) -> list[RateRow]:
        rows = self._conn.execute(
            f"SELECT valid_from, valid_to, value_inc_vat, value_exc_vat FROM {table} WHERE tariff_code=? ORDER BY valid_from",
            (tariff_code,),
        ).fetchall()
        return [
            RateRow(
                valid_from=_parse(r["valid_from"]),  # type: ignore[arg-type]
                valid_to=_parse(r["valid_to"]),
                value_inc_vat=r["value_inc_vat"],
                value_exc_vat=r["value_exc_vat"],
            )
            for r in rows
        ]
```

- [ ] **Step 7: Implement `src/octopus_mcp/cache/meters.py`**

```python
"""Meters and tariff assignment repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


@dataclass(frozen=True)
class MeterRow:
    account_number: str
    fuel: str
    mpan_or_mprn: str
    serial_number: str
    is_export: bool = False


@dataclass(frozen=True)
class TariffAssignmentRow:
    account_number: str
    fuel: str
    product_code: str
    tariff_code: str
    valid_from: datetime
    valid_to: datetime | None


class MetersRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_meters(self, rows: list[MeterRow]) -> None:
        self._conn.executemany(
            """
            INSERT INTO meters (account_number, fuel, mpan_or_mprn, serial_number, is_export)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_number, fuel, mpan_or_mprn, serial_number)
            DO UPDATE SET is_export=excluded.is_export
            """,
            [(r.account_number, r.fuel, r.mpan_or_mprn, r.serial_number, int(r.is_export)) for r in rows],
        )

    def list_meters_for_account(self, account_number: str, *, fuel: str | None = None) -> list[MeterRow]:
        if fuel is not None:
            rs = self._conn.execute(
                "SELECT * FROM meters WHERE account_number=? AND fuel=?", (account_number, fuel)
            ).fetchall()
        else:
            rs = self._conn.execute(
                "SELECT * FROM meters WHERE account_number=?", (account_number,)
            ).fetchall()
        return [
            MeterRow(
                account_number=r["account_number"],
                fuel=r["fuel"],
                mpan_or_mprn=r["mpan_or_mprn"],
                serial_number=r["serial_number"],
                is_export=bool(r["is_export"]),
            )
            for r in rs
        ]

    def upsert_tariff_assignments(self, rows: list[TariffAssignmentRow]) -> None:
        self._conn.executemany(
            """
            INSERT INTO tariff_assignments (account_number, fuel, product_code, tariff_code, valid_from, valid_to)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_number, fuel, valid_from)
            DO UPDATE SET product_code=excluded.product_code,
                          tariff_code=excluded.tariff_code,
                          valid_to=excluded.valid_to
            """,
            [
                (r.account_number, r.fuel, r.product_code, r.tariff_code, _iso(r.valid_from), _iso(r.valid_to))
                for r in rows
            ],
        )

    def current_tariff_assignment(
        self, *, account_number: str, fuel: str, at: datetime
    ) -> TariffAssignmentRow | None:
        row = self._conn.execute(
            """
            SELECT * FROM tariff_assignments
             WHERE account_number=? AND fuel=?
               AND valid_from <= ?
               AND (valid_to IS NULL OR valid_to > ?)
             ORDER BY valid_from DESC LIMIT 1
            """,
            (account_number, fuel, _iso(at), _iso(at)),
        ).fetchone()
        if row is None:
            return None
        return TariffAssignmentRow(
            account_number=row["account_number"],
            fuel=row["fuel"],
            product_code=row["product_code"],
            tariff_code=row["tariff_code"],
            valid_from=_parse(row["valid_from"]),  # type: ignore[arg-type]
            valid_to=_parse(row["valid_to"]),
        )
```

- [ ] **Step 8: Implement `src/octopus_mcp/cache/products.py`**

```python
"""Product catalogue repository."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProductRow:
    code: str
    display_name: str
    brand: str | None
    payload: dict[str, Any]
    fetched_at: datetime


class ProductsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, rows: list[ProductRow]) -> None:
        self._conn.executemany(
            """
            INSERT INTO products (code, display_name, brand, payload_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
              display_name=excluded.display_name,
              brand=excluded.brand,
              payload_json=excluded.payload_json,
              fetched_at=excluded.fetched_at
            """,
            [(r.code, r.display_name, r.brand, json.dumps(r.payload), _iso(r.fetched_at)) for r in rows],
        )

    def list_all(self) -> list[ProductRow]:
        rs = self._conn.execute("SELECT * FROM products ORDER BY code").fetchall()
        return [self._row(r) for r in rs]

    def get_by_code(self, code: str) -> ProductRow | None:
        r = self._conn.execute("SELECT * FROM products WHERE code=?", (code,)).fetchone()
        return self._row(r) if r else None

    @staticmethod
    def _row(r) -> ProductRow:
        return ProductRow(
            code=r["code"],
            display_name=r["display_name"],
            brand=r["brand"],
            payload=json.loads(r["payload_json"]),
            fetched_at=datetime.fromisoformat(r["fetched_at"].replace("Z", "+00:00")),
        )
```

- [ ] **Step 9: Implement `src/octopus_mcp/cache/sync_state.py`**

```python
"""Sync watermarks for incremental and TTL-based syncs."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class SyncStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def touch(self, resource: str, *, at: datetime, ttl_seconds: int | None = None) -> None:
        self._conn.execute(
            """
            INSERT INTO sync_state (resource, last_synced_at, ttl_seconds)
            VALUES (?, ?, ?)
            ON CONFLICT(resource) DO UPDATE SET
              last_synced_at=excluded.last_synced_at,
              ttl_seconds=excluded.ttl_seconds
            """,
            (resource, _iso(at), ttl_seconds),
        )

    def last_synced(self, resource: str) -> datetime | None:
        row = self._conn.execute(
            "SELECT last_synced_at FROM sync_state WHERE resource=?", (resource,)
        ).fetchone()
        return _parse(row["last_synced_at"]) if row else None

    def is_fresh(self, resource: str, *, now: datetime) -> bool:
        row = self._conn.execute(
            "SELECT last_synced_at, ttl_seconds FROM sync_state WHERE resource=?", (resource,)
        ).fetchone()
        if row is None or row["ttl_seconds"] is None:
            return False
        last = _parse(row["last_synced_at"])
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return (now - last) < timedelta(seconds=row["ttl_seconds"])
```

- [ ] **Step 10: Run all cache tests**

```bash
pytest tests/cache/ -v
```

Expected: all tests across all four files PASS.

- [ ] **Step 11: Commit**

```bash
git add src/octopus_mcp/cache/rates.py src/octopus_mcp/cache/meters.py src/octopus_mcp/cache/products.py src/octopus_mcp/cache/sync_state.py tests/cache/
git commit -m "feat(cache): rates, meters, products, sync-state repositories"
```

---

### Task 12: Sync orchestration

**Files:**
- Create: `src/octopus_mcp/cache/sync.py`
- Create: `tests/cache/test_sync.py`

- [ ] **Step 1: Write the failing test**

`tests/cache/test_sync.py`:
```python
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from octopus_mcp.cache.consumption import ConsumptionRepo, ConsumptionRowIn
from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo


@pytest.mark.asyncio
async def test_first_sync_pulls_full_range_and_records_watermark():
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)

    fake_rest = AsyncMock()
    fake_rest.get_electricity_consumption.return_value = [
        type("R", (), dict(consumption=0.5, interval_start=datetime(2026, 4, 25, tzinfo=timezone.utc), interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=timezone.utc)))()
    ]
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    rows = await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
        now=datetime(2026, 4, 26, 12, tzinfo=timezone.utc),
    )
    assert len(rows) == 1
    assert state.last_synced("consumption:electricity:123:S") is not None
    fake_rest.get_electricity_consumption.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_sync_only_fetches_after_watermark():
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)
    repo.upsert([
        ConsumptionRowIn(
            fuel="electricity",
            mpan_or_mprn="123",
            serial_number="S",
            interval_start=datetime(2026, 4, 25, tzinfo=timezone.utc),
            interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=timezone.utc),
            consumption_kwh=0.5,
        )
    ])

    fake_rest = AsyncMock()
    fake_rest.get_electricity_consumption.return_value = []
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 27, tzinfo=timezone.utc),
        now=datetime(2026, 4, 27, 12, tzinfo=timezone.utc),
    )
    call = fake_rest.get_electricity_consumption.await_args
    period_from = call.kwargs["period_from"]
    assert period_from > datetime(2026, 4, 25, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_skip_sync_when_watermark_recent_enough(monkeypatch):
    """If we synced within the last 30 minutes and have data, skip."""
    conn = open_db(":memory:")
    repo = ConsumptionRepo(conn)
    state = SyncStateRepo(conn)
    repo.upsert([
        ConsumptionRowIn(
            fuel="electricity",
            mpan_or_mprn="123",
            serial_number="S",
            interval_start=datetime(2026, 4, 25, tzinfo=timezone.utc),
            interval_end=datetime(2026, 4, 25, 0, 30, tzinfo=timezone.utc),
            consumption_kwh=0.5,
        )
    ])
    state.touch("consumption:electricity:123:S", at=datetime(2026, 4, 27, 12, tzinfo=timezone.utc), ttl_seconds=1800)

    fake_rest = AsyncMock()
    syncer = ConsumptionSyncer(rest=fake_rest, repo=repo, state=state)

    await syncer.ensure(
        fuel="electricity",
        mpan_or_mprn="123",
        serial_number="S",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 25, 12, tzinfo=timezone.utc),
        now=datetime(2026, 4, 27, 12, 15, tzinfo=timezone.utc),
    )
    fake_rest.get_electricity_consumption.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/cache/test_sync.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/cache/sync.py`**

```python
"""Lazy incremental sync orchestration for consumption."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from octopus_mcp.cache.consumption import ConsumptionRepo, ConsumptionRow, ConsumptionRowIn
from octopus_mcp.cache.sync_state import SyncStateRepo

_DEFAULT_TTL = 1800  # 30 minutes — Octopus publishes ~hourly


def _resource_key(fuel: str, mpan_or_mprn: str, serial: str) -> str:
    return f"consumption:{fuel}:{mpan_or_mprn}:{serial}"


@dataclass
class ConsumptionSyncer:
    rest: object  # OctopusRestClient — kept loose for testability
    repo: ConsumptionRepo
    state: SyncStateRepo
    ttl_seconds: int = _DEFAULT_TTL

    async def ensure(
        self,
        *,
        fuel: str,
        mpan_or_mprn: str,
        serial_number: str,
        period_from: datetime,
        period_to: datetime,
        now: datetime | None = None,
    ) -> list[ConsumptionRow]:
        now = now or datetime.now(timezone.utc)
        key = _resource_key(fuel, mpan_or_mprn, serial_number)

        if not self.state.is_fresh(key, now=now):
            await self._fetch_gap(fuel, mpan_or_mprn, serial_number, now)
            self.state.touch(key, at=now, ttl_seconds=self.ttl_seconds)

        return self.repo.get_range(
            fuel=fuel,
            mpan_or_mprn=mpan_or_mprn,
            serial_number=serial_number,
            period_from=period_from,
            period_to=period_to,
        )

    async def _fetch_gap(self, fuel: str, mpan_or_mprn: str, serial: str, now: datetime) -> None:
        watermark = self.repo.latest_interval_start(
            fuel=fuel, mpan_or_mprn=mpan_or_mprn, serial_number=serial
        )
        # If we have a watermark, fetch from the next half-hour. Otherwise pull a year back as a sane default cap.
        from_dt = (watermark + timedelta(minutes=30)) if watermark else (now - timedelta(days=365))

        if fuel == "electricity":
            rows = await self.rest.get_electricity_consumption(  # type: ignore[attr-defined]
                mpan=mpan_or_mprn, serial=serial, period_from=from_dt
            )
        else:
            rows = await self.rest.get_gas_consumption(  # type: ignore[attr-defined]
                mprn=mpan_or_mprn, serial=serial, period_from=from_dt
            )

        if not rows:
            return

        self.repo.upsert(
            [
                ConsumptionRowIn(
                    fuel=fuel,  # type: ignore[arg-type]
                    mpan_or_mprn=mpan_or_mprn,
                    serial_number=serial,
                    interval_start=r.interval_start,
                    interval_end=r.interval_end,
                    consumption_kwh=r.consumption,
                )
                for r in rows
            ]
        )
```

**Known limitation surfaced here, not deferred to a future task:** the Octopus consumption endpoint can return gas values in m³ for some SMETS2 meters rather than kWh. This task stores whatever the API returns. If a user sees implausibly small gas values (~1/11th of expected), they need to convert manually for now — gas-unit normalisation is on the v0.2 roadmap (see "Known limitations" at the bottom of this plan). To make the issue visible, add a warning log when a single gas row's value is `< 0.05` for a 30-min slot in winter (likely m³, not kWh):

```python
        if fuel == "gas":
            import logging
            log = logging.getLogger(__name__)
            for r in rows[:5]:
                if r.consumption < 0.05:
                    log.warning(
                        "gas value looks small (%.4f); meter may report m³, not kWh — see README known limitations",
                        r.consumption,
                    )
                    break
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/cache/test_sync.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/cache/sync.py tests/cache/test_sync.py
git commit -m "feat(cache): lazy incremental consumption sync orchestrator"
```

---

## CHECKPOINT — Phase 0–2 complete

At this point you have:
- A clean Python package with CI, lint, type-check, secret-scanning.
- A typed REST client that can talk to Octopus.
- A SQLite cache with a watermark-driven sync orchestrator.

Nothing user-facing yet. The next phases build the analysis, tools, server, CLI, and plugin on top of this.

---

## Phase 3 — Analysis (pure functions)

### Task 13: Rate step-function

**Files:**
- Create: `src/octopus_mcp/analysis/__init__.py`
- Create: `src/octopus_mcp/analysis/rate_lookup.py`
- Create: `tests/analysis/__init__.py`
- Create: `tests/analysis/test_rate_lookup.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_rate_lookup.py`:
```python
from datetime import datetime, timezone

import pytest

from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow


def _w(start: str, end: str | None, value: float) -> RateWindow:
    s = datetime.fromisoformat(start.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None
    return RateWindow(valid_from=s, valid_to=e, value_inc_vat=value)


def test_rate_at_picks_active_window():
    stream = RateStream([
        _w("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", 26.25),
        _w("2026-04-01T00:00:00Z", None, 25.20),
    ])
    assert stream.rate_at(datetime(2026, 2, 15, tzinfo=timezone.utc)) == 26.25
    assert stream.rate_at(datetime(2026, 4, 15, tzinfo=timezone.utc)) == 25.20


def test_rate_at_returns_none_before_first_window():
    stream = RateStream([_w("2026-04-01T00:00:00Z", None, 25.20)])
    assert stream.rate_at(datetime(2026, 1, 1, tzinfo=timezone.utc)) is None


def test_rate_at_open_ended_window():
    stream = RateStream([_w("2026-04-01T00:00:00Z", None, 25.20)])
    assert stream.rate_at(datetime(2030, 1, 1, tzinfo=timezone.utc)) == 25.20


def test_unsorted_input_is_normalised():
    stream = RateStream([
        _w("2026-04-01T00:00:00Z", None, 25.20),
        _w("2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z", 26.25),
    ])
    assert stream.rate_at(datetime(2026, 2, 1, tzinfo=timezone.utc)) == 26.25


def test_empty_stream_returns_none():
    assert RateStream([]).rate_at(datetime(2026, 1, 1, tzinfo=timezone.utc)) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_rate_lookup.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/analysis/rate_lookup.py`**

```python
"""Step-function lookup over a tariff rate stream."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RateWindow:
    valid_from: datetime
    valid_to: datetime | None
    value_inc_vat: float


class RateStream:
    """Sorted rate windows; O(log n) lookup."""

    def __init__(self, windows: list[RateWindow]) -> None:
        self._windows = sorted(windows, key=lambda w: w.valid_from)
        self._starts = [w.valid_from for w in self._windows]

    def rate_at(self, ts: datetime) -> float | None:
        if not self._windows:
            return None
        i = bisect_right(self._starts, ts) - 1
        if i < 0:
            return None
        win = self._windows[i]
        if win.valid_to is not None and ts >= win.valid_to:
            return None
        return win.value_inc_vat
```

- [ ] **Step 4: Create empty `src/octopus_mcp/analysis/__init__.py` and `tests/analysis/__init__.py`**

- [ ] **Step 5: Run tests**

```bash
pytest tests/analysis/test_rate_lookup.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/octopus_mcp/analysis/ tests/analysis/
git commit -m "feat(analysis): rate-stream step-function lookup"
```

---

### Task 14: Billing math (period cost)

**Files:**
- Create: `src/octopus_mcp/analysis/billing.py`
- Create: `tests/analysis/test_billing.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_billing.py`:
```python
from datetime import datetime, timezone

from octopus_mcp.analysis.billing import (
    ConsumptionPoint,
    PeriodCost,
    compute_period_cost,
)
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow


def _r(start_iso: str, end_iso: str | None, value: float) -> RateWindow:
    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00")) if end_iso else None
    return RateWindow(valid_from=s, valid_to=e, value_inc_vat=value)


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_unit_cost_is_kwh_times_rate_summed_in_pence():
    consumption = [_c("2026-04-25T00:00:00Z", 1.0), _c("2026-04-25T00:30:00Z", 0.5)]
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.20)])
    sc_stream = RateStream([_r("2026-04-01T00:00:00Z", None, 50.0)])

    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc_stream,
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert isinstance(result, PeriodCost)
    # 1.5 kWh * 25.20p = 37.8p -> rounded to 38p
    assert result.unit_pence == 38
    # 1 day * 50p = 50p
    assert result.standing_pence == 50
    assert result.total_pence == 88


def test_standing_charge_prorates_over_period_in_full_days():
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.0)])
    sc_stream = RateStream([_r("2026-04-01T00:00:00Z", None, 60.0)])

    result = compute_period_cost(
        consumption=[],
        unit_rates=rates,
        standing_charges=sc_stream,
        period_from=datetime(2026, 4, 1, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 8, tzinfo=timezone.utc),
    )
    # 7 days * 60p = 420p
    assert result.standing_pence == 420


def test_consumption_outside_period_is_excluded():
    rates = RateStream([_r("2026-04-01T00:00:00Z", None, 25.0)])
    sc = RateStream([_r("2026-04-01T00:00:00Z", None, 0.0)])
    consumption = [
        _c("2026-04-24T23:30:00Z", 1.0),  # before period
        _c("2026-04-25T00:00:00Z", 2.0),  # inside
        _c("2026-04-26T00:00:00Z", 4.0),  # at boundary, exclusive
    ]
    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc,
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    # Only 2.0 kWh counted: 50p -> 50p
    assert result.unit_pence == 50


def test_missing_rate_skips_consumption_with_caveat():
    consumption = [_c("2026-04-25T00:00:00Z", 1.0)]
    rates = RateStream([])  # no rates
    sc = RateStream([])

    result = compute_period_cost(
        consumption=consumption,
        unit_rates=rates,
        standing_charges=sc,
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
    )
    assert result.unit_pence == 0
    assert any("missing rate" in c.lower() for c in result.caveats)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_billing.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/analysis/billing.py`**

```python
"""Period billing math: unit cost + standing charge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from octopus_mcp.analysis.rate_lookup import RateStream


@dataclass(frozen=True)
class ConsumptionPoint:
    interval_start: datetime
    consumption_kwh: float


@dataclass(frozen=True)
class PeriodCost:
    unit_pence: int
    standing_pence: int
    total_pence: int
    caveats: list[str] = field(default_factory=list)


def _round_pence(value_pence_float: float) -> int:
    return int(round(value_pence_float))


def compute_period_cost(
    *,
    consumption: Iterable[ConsumptionPoint],
    unit_rates: RateStream,
    standing_charges: RateStream,
    period_from: datetime,
    period_to: datetime,
) -> PeriodCost:
    caveats: list[str] = []

    # --- unit cost ---
    unit_total_p = 0.0
    skipped = 0
    for c in consumption:
        if c.interval_start < period_from or c.interval_start >= period_to:
            continue
        rate = unit_rates.rate_at(c.interval_start)
        if rate is None:
            skipped += 1
            continue
        unit_total_p += c.consumption_kwh * rate
    if skipped:
        caveats.append(f"Skipped {skipped} half-hour(s) with missing rate data")

    # --- standing charge: per-day proration ---
    day = period_from.replace(hour=0, minute=0, second=0, microsecond=0)
    if day.tzinfo is None:
        day = day.replace(tzinfo=timezone.utc)
    end = period_to
    standing_total_p = 0.0
    standing_skipped = 0
    while day < end:
        rate = standing_charges.rate_at(day)
        if rate is None:
            standing_skipped += 1
        else:
            standing_total_p += rate
        day += timedelta(days=1)
    if standing_skipped:
        caveats.append(f"Missing standing charge for {standing_skipped} day(s)")

    unit_p = _round_pence(unit_total_p)
    standing_p = _round_pence(standing_total_p)
    return PeriodCost(unit_pence=unit_p, standing_pence=standing_p, total_pence=unit_p + standing_p, caveats=caveats)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/analysis/test_billing.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/analysis/billing.py tests/analysis/test_billing.py
git commit -m "feat(analysis): period billing math (unit + standing, integer pence)"
```

---

### Task 15: Tariff comparison engine

**Files:**
- Create: `src/octopus_mcp/analysis/tariff_comparison.py`
- Create: `tests/analysis/test_tariff_comparison.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_tariff_comparison.py`:
```python
from datetime import datetime, timezone

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow
from octopus_mcp.analysis.tariff_comparison import (
    FuelComparison,
    FuelInputs,
    TariffComparison,
    compare_tariffs,
)


def _w(start: str, end: str | None, v: float) -> RateWindow:
    s = datetime.fromisoformat(start.replace("Z", "+00:00"))
    e = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None
    return RateWindow(valid_from=s, valid_to=e, value_inc_vat=v)


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_target_cheaper_yields_negative_delta():
    consumption = [_c("2026-04-25T00:00:00Z", 1.0), _c("2026-04-25T00:30:00Z", 1.0)]
    current_unit = RateStream([_w("2026-04-01T00:00:00Z", None, 30.0)])
    target_unit = RateStream([_w("2026-04-01T00:00:00Z", None, 20.0)])
    sc = RateStream([_w("2026-04-01T00:00:00Z", None, 50.0)])

    inputs = [
        FuelInputs(
            fuel="electricity",
            consumption=consumption,
            current_unit_rates=current_unit,
            current_standing=sc,
            target_unit_rates=target_unit,
            target_standing=sc,
        )
    ]
    result = compare_tariffs(
        target_product_code="GO-VAR-22-10-14",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
        fuels=inputs,
    )
    assert isinstance(result, TariffComparison)
    fc: FuelComparison = result.fuels[0]
    # current: 2 kWh * 30p = 60p + 50p standing = 110p
    # target:  2 kWh * 20p = 40p + 50p standing = 90p
    assert fc.current_total_pence == 110
    assert fc.target_total_pence == 90
    assert fc.delta_pence == -20
    assert result.total_delta_pence == -20
    assert "saves" in result.pounds_summary.lower() or "save" in result.pounds_summary.lower()


def test_includes_default_caveats():
    inputs = [
        FuelInputs(
            fuel="electricity",
            consumption=[],
            current_unit_rates=RateStream([_w("2026-04-01T00:00:00Z", None, 30.0)]),
            current_standing=RateStream([_w("2026-04-01T00:00:00Z", None, 50.0)]),
            target_unit_rates=RateStream([_w("2026-04-01T00:00:00Z", None, 20.0)]),
            target_standing=RateStream([_w("2026-04-01T00:00:00Z", None, 50.0)]),
        )
    ]
    result = compare_tariffs(
        target_product_code="X",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 26, tzinfo=timezone.utc),
        fuels=inputs,
    )
    text = " ".join(result.caveats).lower()
    assert "saving sessions" in text
    assert "behaviour" in text or "behavior" in text


def test_per_day_breakdown_present():
    consumption = [
        _c("2026-04-25T12:00:00Z", 2.0),
        _c("2026-04-26T12:00:00Z", 3.0),
    ]
    inputs = [
        FuelInputs(
            fuel="electricity",
            consumption=consumption,
            current_unit_rates=RateStream([_w("2026-04-01T00:00:00Z", None, 30.0)]),
            current_standing=RateStream([_w("2026-04-01T00:00:00Z", None, 50.0)]),
            target_unit_rates=RateStream([_w("2026-04-01T00:00:00Z", None, 20.0)]),
            target_standing=RateStream([_w("2026-04-01T00:00:00Z", None, 50.0)]),
        )
    ]
    result = compare_tariffs(
        target_product_code="X",
        period_from=datetime(2026, 4, 25, tzinfo=timezone.utc),
        period_to=datetime(2026, 4, 27, tzinfo=timezone.utc),
        fuels=inputs,
    )
    assert len(result.breakdown_by_day) == 2
    days = [d.date.isoformat() for d in result.breakdown_by_day]
    assert "2026-04-25" in days
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_tariff_comparison.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/analysis/tariff_comparison.py`**

```python
"""Tariff comparison: replay actual usage against another tariff."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from octopus_mcp.analysis.billing import ConsumptionPoint, compute_period_cost
from octopus_mcp.analysis.rate_lookup import RateStream

_DEFAULT_CAVEATS = [
    "Models a pure tariff swap; does not include Saving Sessions, Octoplus, or referral credits.",
    "Assumes your usage pattern is unchanged on the target tariff. Time-of-use tariffs typically reward behaviour change — actual savings often higher.",
]


@dataclass(frozen=True)
class FuelInputs:
    fuel: Literal["electricity", "gas"]
    consumption: list[ConsumptionPoint]
    current_unit_rates: RateStream
    current_standing: RateStream
    target_unit_rates: RateStream
    target_standing: RateStream


@dataclass(frozen=True)
class FuelComparison:
    fuel: str
    current_unit_pence: int
    current_standing_pence: int
    current_total_pence: int
    target_unit_pence: int
    target_standing_pence: int
    target_total_pence: int
    delta_pence: int


@dataclass(frozen=True)
class DayBreakdown:
    date: date
    current_pence: int
    target_pence: int
    delta_pence: int


@dataclass(frozen=True)
class TariffComparison:
    period: tuple[date, date]
    target_product_code: str
    fuels: list[FuelComparison]
    total_current_pence: int
    total_target_pence: int
    total_delta_pence: int
    pounds_summary: str
    breakdown_by_day: list[DayBreakdown]
    caveats: list[str] = field(default_factory=list)


def _format_pounds(delta_pence: int) -> str:
    abs_pounds = abs(delta_pence) / 100.0
    if delta_pence < 0:
        return f"Saves £{abs_pounds:.2f}"
    if delta_pence > 0:
        return f"Costs £{abs_pounds:.2f} more"
    return "Same cost"


def compare_tariffs(
    *,
    target_product_code: str,
    period_from: datetime,
    period_to: datetime,
    fuels: list[FuelInputs],
) -> TariffComparison:
    fuel_results: list[FuelComparison] = []
    day_buckets: dict[date, tuple[int, int]] = {}

    for f in fuels:
        cur = compute_period_cost(
            consumption=f.consumption,
            unit_rates=f.current_unit_rates,
            standing_charges=f.current_standing,
            period_from=period_from,
            period_to=period_to,
        )
        tgt = compute_period_cost(
            consumption=f.consumption,
            unit_rates=f.target_unit_rates,
            standing_charges=f.target_standing,
            period_from=period_from,
            period_to=period_to,
        )
        fuel_results.append(
            FuelComparison(
                fuel=f.fuel,
                current_unit_pence=cur.unit_pence,
                current_standing_pence=cur.standing_pence,
                current_total_pence=cur.total_pence,
                target_unit_pence=tgt.unit_pence,
                target_standing_pence=tgt.standing_pence,
                target_total_pence=tgt.total_pence,
                delta_pence=tgt.total_pence - cur.total_pence,
            )
        )

        # day-level breakdown by re-running per-day
        d = period_from.date()
        end_d = period_to.date()
        while d < end_d:
            day_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            day_end = day_start + timedelta(days=1)
            cur_d = compute_period_cost(
                consumption=f.consumption,
                unit_rates=f.current_unit_rates,
                standing_charges=f.current_standing,
                period_from=day_start,
                period_to=day_end,
            )
            tgt_d = compute_period_cost(
                consumption=f.consumption,
                unit_rates=f.target_unit_rates,
                standing_charges=f.target_standing,
                period_from=day_start,
                period_to=day_end,
            )
            cur_p, tgt_p = day_buckets.get(d, (0, 0))
            day_buckets[d] = (cur_p + cur_d.total_pence, tgt_p + tgt_d.total_pence)
            d += timedelta(days=1)

    breakdown = [
        DayBreakdown(date=d, current_pence=c, target_pence=t, delta_pence=t - c)
        for d, (c, t) in sorted(day_buckets.items())
    ]

    total_current = sum(f.current_total_pence for f in fuel_results)
    total_target = sum(f.target_total_pence for f in fuel_results)
    total_delta = total_target - total_current

    return TariffComparison(
        period=(period_from.date(), period_to.date()),
        target_product_code=target_product_code,
        fuels=fuel_results,
        total_current_pence=total_current,
        total_target_pence=total_target,
        total_delta_pence=total_delta,
        pounds_summary=_format_pounds(total_delta),
        breakdown_by_day=breakdown,
        caveats=list(_DEFAULT_CAVEATS),
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/analysis/test_tariff_comparison.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/analysis/tariff_comparison.py tests/analysis/test_tariff_comparison.py
git commit -m "feat(analysis): tariff comparison engine with per-day breakdown and caveats"
```

---

### Task 16: Aggregations (group_by) + stats

**Files:**
- Create: `src/octopus_mcp/analysis/aggregations.py`
- Create: `tests/analysis/test_aggregations.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_aggregations.py`:
```python
from datetime import datetime, timezone

from octopus_mcp.analysis.aggregations import GroupBy, aggregate, summary_stats
from octopus_mcp.analysis.billing import ConsumptionPoint


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_aggregate_by_day_sums_per_local_day():
    rows = [
        _c("2026-04-25T00:00:00Z", 1.0),
        _c("2026-04-25T12:00:00Z", 2.0),
        _c("2026-04-26T00:00:00Z", 4.0),
    ]
    out = aggregate(rows, group_by=GroupBy.DAY, tz="Europe/London")
    assert len(out) == 2
    assert out[0].label == "2026-04-25"
    assert out[0].kwh == 3.0
    assert out[1].kwh == 4.0


def test_aggregate_by_hour_buckets_half_hours():
    rows = [
        _c("2026-04-25T08:00:00Z", 0.5),
        _c("2026-04-25T08:30:00Z", 0.7),
        _c("2026-04-25T09:00:00Z", 0.4),
    ]
    out = aggregate(rows, group_by=GroupBy.HOUR, tz="Europe/London")
    labels = [b.label for b in out]
    # In April London is BST (UTC+1)
    assert labels[0] == "2026-04-25 09:00"
    assert out[0].kwh == 1.2


def test_summary_stats_min_max_mean_stdev():
    s = summary_stats([1.0, 2.0, 3.0, 4.0])
    assert s.min == 1.0
    assert s.max == 4.0
    assert s.mean == 2.5
    assert round(s.stdev, 4) == 1.2910


def test_summary_stats_empty_returns_zeros():
    s = summary_stats([])
    assert s.min == s.max == s.mean == s.stdev == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_aggregations.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/analysis/aggregations.py`**

```python
"""Time-bucket aggregations and summary statistics."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Iterable
from zoneinfo import ZoneInfo

from octopus_mcp.analysis.billing import ConsumptionPoint


class GroupBy(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class Bucket:
    label: str
    kwh: float


@dataclass(frozen=True)
class Stats:
    min: float
    max: float
    mean: float
    stdev: float


def _bucket_label(local: datetime, group_by: GroupBy) -> str:
    if group_by == GroupBy.HOUR:
        return local.strftime("%Y-%m-%d %H:00")
    if group_by == GroupBy.DAY:
        return local.strftime("%Y-%m-%d")
    if group_by == GroupBy.WEEK:
        iso_year, iso_week, _ = local.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if group_by == GroupBy.MONTH:
        return local.strftime("%Y-%m")
    raise ValueError(group_by)


def aggregate(
    rows: Iterable[ConsumptionPoint],
    *,
    group_by: GroupBy,
    tz: str = "Europe/London",
) -> list[Bucket]:
    zone = ZoneInfo(tz)
    buckets: dict[str, float] = defaultdict(float)
    for r in rows:
        local = r.interval_start.astimezone(zone)
        if group_by == GroupBy.HOUR:
            local = local.replace(minute=0, second=0, microsecond=0)
        elif group_by == GroupBy.DAY:
            local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        label = _bucket_label(local, group_by)
        buckets[label] += r.consumption_kwh
    return [Bucket(label=k, kwh=round(v, 4)) for k, v in sorted(buckets.items())]


def summary_stats(values: list[float]) -> Stats:
    if not values:
        return Stats(0.0, 0.0, 0.0, 0.0)
    return Stats(
        min=min(values),
        max=max(values),
        mean=statistics.mean(values),
        stdev=statistics.stdev(values) if len(values) > 1 else 0.0,
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/analysis/test_aggregations.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/analysis/aggregations.py tests/analysis/test_aggregations.py
git commit -m "feat(analysis): time-bucket aggregations and summary stats"
```

---

### Task 17: Peak detection

**Files:**
- Create: `src/octopus_mcp/analysis/peaks.py`
- Create: `tests/analysis/test_peaks.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_peaks.py`:
```python
from datetime import datetime, timezone

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.analysis.peaks import top_n_half_hours


def _c(iso: str, kwh: float) -> ConsumptionPoint:
    return ConsumptionPoint(
        interval_start=datetime.fromisoformat(iso.replace("Z", "+00:00")), consumption_kwh=kwh
    )


def test_returns_top_n_descending():
    rows = [
        _c("2026-04-25T00:00:00Z", 0.3),
        _c("2026-04-25T18:00:00Z", 2.5),
        _c("2026-04-25T19:00:00Z", 3.1),
        _c("2026-04-25T20:00:00Z", 1.8),
    ]
    peaks = top_n_half_hours(rows, n=2)
    assert len(peaks) == 2
    assert peaks[0].consumption_kwh == 3.1
    assert peaks[1].consumption_kwh == 2.5


def test_n_larger_than_input_returns_all_sorted():
    rows = [_c("2026-04-25T00:00:00Z", 0.1), _c("2026-04-25T01:00:00Z", 0.2)]
    peaks = top_n_half_hours(rows, n=10)
    assert len(peaks) == 2
    assert peaks[0].consumption_kwh == 0.2


def test_empty_input_returns_empty():
    assert top_n_half_hours([], n=5) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_peaks.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/analysis/peaks.py`**

```python
"""Peak-half-hour detection."""

from __future__ import annotations

from typing import Iterable

from octopus_mcp.analysis.billing import ConsumptionPoint


def top_n_half_hours(rows: Iterable[ConsumptionPoint], *, n: int) -> list[ConsumptionPoint]:
    return sorted(rows, key=lambda r: r.consumption_kwh, reverse=True)[:n]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/analysis/test_peaks.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/analysis/peaks.py tests/analysis/test_peaks.py
git commit -m "feat(analysis): top-N half-hour peak detection"
```

---

## Phase 4 — Tools layer

### Task 18: Period spec + thin getters

**Files:**
- Create: `src/octopus_mcp/tools/__init__.py`
- Create: `src/octopus_mcp/tools/period.py`
- Create: `src/octopus_mcp/tools/context.py`
- Create: `src/octopus_mcp/tools/thin.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/test_period.py`
- Create: `tests/tools/test_thin.py`

- [ ] **Step 1: Write `tests/tools/test_period.py`**

```python
from datetime import date, datetime, timezone

import pytest

from octopus_mcp.tools.period import PeriodSpec, resolve_period


def _now() -> datetime:
    return datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)


def test_last_month():
    pf, pt = resolve_period(PeriodSpec(kind="last_month"), now=_now())
    assert (pf.year, pf.month, pf.day) == (2026, 3, 1)
    assert (pt.year, pt.month, pt.day) == (2026, 4, 1)


def test_last_7_days():
    pf, pt = resolve_period(PeriodSpec(kind="last_7_days"), now=_now())
    assert (pt - pf).days == 7


def test_explicit_range():
    pf, pt = resolve_period(
        PeriodSpec(kind="explicit", from_date=date(2026, 4, 1), to_date=date(2026, 4, 15)),
        now=_now(),
    )
    assert pf.date() == date(2026, 4, 1) and pt.date() == date(2026, 4, 15)


def test_period_too_long_rejected():
    with pytest.raises(ValueError):
        PeriodSpec(kind="explicit", from_date=date(2020, 1, 1), to_date=date(2025, 1, 1))


def test_period_in_future_rejected():
    with pytest.raises(ValueError):
        resolve_period(
            PeriodSpec(kind="explicit", from_date=date(2030, 1, 1), to_date=date(2030, 1, 2)),
            now=_now(),
        )
```

- [ ] **Step 2: Write `tests/tools/test_thin.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from octopus_mcp.octopus.models import Account, Property
from octopus_mcp.tools.thin import get_account


@pytest.mark.asyncio
async def test_get_account_returns_summary_dict():
    fake_rest = AsyncMock()
    fake_rest.get_account.return_value = Account(
        number="A-12345678",
        properties=[Property(id=1, electricity_meter_points=[], gas_meter_points=[])],
    )
    out = await get_account(rest=fake_rest)
    assert out["number"] == "A-12345678"
    assert "properties" in out
```

- [ ] **Step 3: Run failing tests**

```bash
pytest tests/tools/ -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/octopus_mcp/tools/period.py`**

```python
"""Period specification + resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal


PeriodKind = Literal["last_month", "last_7_days", "last_quarter", "ytd", "explicit"]


@dataclass(frozen=True)
class PeriodSpec:
    kind: PeriodKind
    from_date: date | None = None
    to_date: date | None = None

    def __post_init__(self) -> None:
        if self.kind == "explicit":
            if self.from_date is None or self.to_date is None:
                raise ValueError("explicit period requires from_date and to_date")
            if self.from_date >= self.to_date:
                raise ValueError("from_date must be before to_date")
            if (self.to_date - self.from_date).days > 366 * 2:
                raise ValueError("period exceeds maximum of 2 years")


def _start_of(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def resolve_period(spec: PeriodSpec, *, now: datetime) -> tuple[datetime, datetime]:
    if spec.kind == "last_7_days":
        end = _start_of(now.date())
        return end - timedelta(days=7), end
    if spec.kind == "last_month":
        first_this = now.date().replace(day=1)
        last_first = (first_this - timedelta(days=1)).replace(day=1)
        return _start_of(last_first), _start_of(first_this)
    if spec.kind == "last_quarter":
        end = _start_of(now.date().replace(day=1))
        # 3 months back from this month's first
        m = end.month - 3
        y = end.year
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        return start, end
    if spec.kind == "ytd":
        return datetime(now.year, 1, 1, tzinfo=timezone.utc), _start_of(now.date())
    if spec.kind == "explicit":
        assert spec.from_date and spec.to_date  # validated in __post_init__
        if _start_of(spec.to_date) > now:
            raise ValueError("period extends into the future")
        return _start_of(spec.from_date), _start_of(spec.to_date)
    raise ValueError(f"unknown PeriodKind: {spec.kind}")
```

- [ ] **Step 5: Implement `src/octopus_mcp/tools/context.py`**

```python
"""Shared per-server context handed to each tool."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from octopus_mcp.cache.consumption import ConsumptionRepo
from octopus_mcp.cache.meters import MetersRepo
from octopus_mcp.cache.products import ProductsRepo
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo
from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.rest import OctopusRestClient


@dataclass
class ToolContext:
    creds: OctopusCredentials
    rest: OctopusRestClient
    conn: sqlite3.Connection
    consumption_repo: ConsumptionRepo
    rates_repo: RatesRepo
    meters_repo: MetersRepo
    products_repo: ProductsRepo
    sync_state: SyncStateRepo
    consumption_syncer: ConsumptionSyncer
```

- [ ] **Step 6: Implement `src/octopus_mcp/tools/thin.py`**

```python
"""Thin pass-through tools."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


async def get_account(*, rest) -> dict[str, Any]:
    account = await rest.get_account()
    return account.model_dump(mode="json")


async def list_products(*, rest) -> list[dict[str, Any]]:
    products = await rest.list_products()
    return [p.model_dump(mode="json") for p in products]


async def get_product(code: str, *, rest) -> dict[str, Any]:
    return await rest.get_product(code)


async def get_consumption_raw(
    fuel: str,
    mpan_or_mprn: str,
    serial_number: str,
    period_from: datetime,
    period_to: datetime,
    *,
    rest,
) -> list[dict[str, Any]]:
    if fuel == "electricity":
        rows = await rest.get_electricity_consumption(
            mpan=mpan_or_mprn, serial=serial_number, period_from=period_from, period_to=period_to
        )
    else:
        rows = await rest.get_gas_consumption(
            mprn=mpan_or_mprn, serial=serial_number, period_from=period_from, period_to=period_to
        )
    return [
        {
            "interval_start": r.interval_start.isoformat(),
            "interval_end": r.interval_end.isoformat(),
            "consumption_kwh": r.consumption,
        }
        for r in rows
    ]
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/tools/ -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add src/octopus_mcp/tools/ tests/tools/
git commit -m "feat(tools): period spec, tool context, thin getter tools"
```

---

### Task 19: Thick tools — `bill_summary` and `current_tariff`

**Files:**
- Create: `src/octopus_mcp/tools/bill_summary.py`
- Create: `src/octopus_mcp/tools/current_tariff.py`
- Create: `tests/tools/test_bill_summary.py`
- Create: `tests/tools/test_current_tariff.py`

- [ ] **Step 1: Write `tests/tools/test_bill_summary.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.cache.meters import MeterRow, TariffAssignmentRow
from octopus_mcp.cache.rates import RateRow
from octopus_mcp.tools.bill_summary import bill_summary
from octopus_mcp.tools.period import PeriodSpec


@pytest.mark.asyncio
async def test_bill_summary_basic_electricity_only():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.list_meters_for_account.return_value = [
        MeterRow(account_number="A-1", fuel="electricity", mpan_or_mprn="123", serial_number="S")
    ]
    ctx.meters_repo.current_tariff_assignment.return_value = TariffAssignmentRow(
        account_number="A-1",
        fuel="electricity",
        product_code="VAR",
        tariff_code="E-1R-VAR",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=None,
    )

    consumer_syncer = AsyncMock()
    ctx.consumption_syncer = consumer_syncer

    class _R:
        def __init__(self, iso, kwh):
            self.interval_start = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            self.interval_end = self.interval_start
            self.consumption_kwh = kwh

    consumer_syncer.ensure.return_value = [
        _R("2026-03-01T00:00:00Z", 1.0),
        _R("2026-03-15T00:00:00Z", 1.0),
    ]
    ctx.rates_repo.get_unit_rates.return_value = [
        RateRow(valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=25.0, value_exc_vat=23.0)
    ]
    ctx.rates_repo.get_standing_charges.return_value = [
        RateRow(valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=50.0, value_exc_vat=47.0)
    ]
    # No-op rate sync stub
    async def _ensure_rates(*a, **k): return None
    ctx.ensure_rates = _ensure_rates

    out = await bill_summary(period=PeriodSpec(kind="last_month"), ctx=ctx, now=datetime(2026, 4, 1, tzinfo=timezone.utc))
    assert out["fuels"][0]["fuel"] == "electricity"
    # 2 kWh * 25p = 50p; 31 days * 50p = 1550p. Total 1600p.
    assert out["fuels"][0]["unit_pence"] == 50
    assert out["fuels"][0]["standing_pence"] == 1550
    assert out["totals"]["total_pence"] == 1600


@pytest.mark.asyncio
async def test_bill_summary_no_gas_meter_lists_unavailable():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.list_meters_for_account.return_value = [
        MeterRow(account_number="A-1", fuel="electricity", mpan_or_mprn="123", serial_number="S")
    ]
    ctx.meters_repo.current_tariff_assignment.return_value = TariffAssignmentRow(
        account_number="A-1", fuel="electricity", product_code="VAR", tariff_code="E-1R",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None,
    )
    ctx.rates_repo.get_unit_rates.return_value = []
    ctx.rates_repo.get_standing_charges.return_value = []
    ctx.consumption_syncer.ensure = AsyncMock(return_value=[])
    async def _ensure_rates(*a, **k): return None
    ctx.ensure_rates = _ensure_rates

    out = await bill_summary(period=PeriodSpec(kind="last_month"), ctx=ctx, now=datetime(2026, 4, 1, tzinfo=timezone.utc))
    assert "gas" in out["fuels_unavailable"]
```

- [ ] **Step 2: Write `tests/tools/test_current_tariff.py`**

```python
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from octopus_mcp.cache.meters import TariffAssignmentRow
from octopus_mcp.cache.rates import RateRow
from octopus_mcp.tools.current_tariff import current_tariff


@pytest.mark.asyncio
async def test_current_tariff_returns_active_assignment_and_latest_rate():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.current_tariff_assignment.return_value = TariffAssignmentRow(
        account_number="A-1",
        fuel="electricity",
        product_code="VAR-22-11-01",
        tariff_code="E-1R-VAR-22-11-01-A",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=None,
    )
    ctx.rates_repo.get_unit_rates.return_value = [
        RateRow(valid_from=datetime(2026, 4, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=25.20, value_exc_vat=24.0),
    ]
    ctx.rates_repo.get_standing_charges.return_value = [
        RateRow(valid_from=datetime(2026, 4, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=50.0, value_exc_vat=47.0),
    ]

    async def _ensure_rates(*a, **k): return None
    ctx.ensure_rates = _ensure_rates

    out = await current_tariff(ctx=ctx, now=datetime(2026, 4, 25, tzinfo=timezone.utc))
    elec = next(f for f in out["fuels"] if f["fuel"] == "electricity")
    assert elec["product_code"] == "VAR-22-11-01"
    assert elec["unit_rate_pence_inc_vat"] == 25.20
    assert elec["standing_charge_pence_inc_vat"] == 50.0
```

- [ ] **Step 3: Run failing tests**

```bash
pytest tests/tools/test_bill_summary.py tests/tools/test_current_tariff.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/octopus_mcp/tools/bill_summary.py`**

```python
"""bill_summary thick tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from octopus_mcp.analysis.billing import ConsumptionPoint, compute_period_cost
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow
from octopus_mcp.tools.period import PeriodSpec, resolve_period


def _windows(rows) -> list[RateWindow]:
    return [RateWindow(valid_from=r.valid_from, valid_to=r.valid_to, value_inc_vat=r.value_inc_vat) for r in rows]


async def bill_summary(*, period: PeriodSpec, ctx, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    period_from, period_to = resolve_period(period, now=now)

    fuels_present: list[str] = []
    fuels_unavailable: list[str] = []
    fuel_outputs: list[dict[str, Any]] = []
    total_pence = 0

    for fuel in ("electricity", "gas"):
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=fuel)
        if not meters:
            fuels_unavailable.append(fuel)
            continue
        fuels_present.append(fuel)
        meter = meters[0]
        assignment = ctx.meters_repo.current_tariff_assignment(
            account_number=ctx.creds.account_number, fuel=fuel, at=period_from
        )
        if assignment is None:
            fuels_unavailable.append(fuel)
            continue

        await ctx.ensure_rates(
            product_code=assignment.product_code,
            tariff_code=assignment.tariff_code,
            fuel=fuel,
        )

        unit_rate_rows = ctx.rates_repo.get_unit_rates(assignment.tariff_code)
        sc_rate_rows = ctx.rates_repo.get_standing_charges(assignment.tariff_code)

        consumption_rows = await ctx.consumption_syncer.ensure(
            fuel=fuel,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        consumption = [
            ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh)
            for r in consumption_rows
        ]
        cost = compute_period_cost(
            consumption=consumption,
            unit_rates=RateStream(_windows(unit_rate_rows)),
            standing_charges=RateStream(_windows(sc_rate_rows)),
            period_from=period_from,
            period_to=period_to,
        )
        total_kwh = sum(c.consumption_kwh for c in consumption if period_from <= c.interval_start < period_to)
        total_pence += cost.total_pence
        fuel_outputs.append(
            {
                "fuel": fuel,
                "tariff_code": assignment.tariff_code,
                "kwh": round(total_kwh, 4),
                "unit_pence": cost.unit_pence,
                "standing_pence": cost.standing_pence,
                "total_pence": cost.total_pence,
                "caveats": cost.caveats,
            }
        )

    return {
        "period": {"from": period_from.date().isoformat(), "to": period_to.date().isoformat()},
        "fuels": fuel_outputs,
        "fuels_unavailable": fuels_unavailable,
        "totals": {"total_pence": total_pence, "pounds": f"£{total_pence / 100:.2f}"},
    }
```

- [ ] **Step 5: Implement `src/octopus_mcp/tools/current_tariff.py`**

```python
"""current_tariff thick tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


async def current_tariff(*, ctx, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    out: list[dict[str, Any]] = []

    for fuel in ("electricity", "gas"):
        assignment = ctx.meters_repo.current_tariff_assignment(
            account_number=ctx.creds.account_number, fuel=fuel, at=now
        )
        if assignment is None:
            continue
        await ctx.ensure_rates(
            product_code=assignment.product_code,
            tariff_code=assignment.tariff_code,
            fuel=fuel,
        )
        unit_rates = ctx.rates_repo.get_unit_rates(assignment.tariff_code)
        sc_rates = ctx.rates_repo.get_standing_charges(assignment.tariff_code)
        latest_unit = max(unit_rates, key=lambda r: r.valid_from) if unit_rates else None
        latest_sc = max(sc_rates, key=lambda r: r.valid_from) if sc_rates else None
        out.append(
            {
                "fuel": fuel,
                "product_code": assignment.product_code,
                "tariff_code": assignment.tariff_code,
                "unit_rate_pence_inc_vat": latest_unit.value_inc_vat if latest_unit else None,
                "standing_charge_pence_inc_vat": latest_sc.value_inc_vat if latest_sc else None,
            }
        )

    return {"as_of": now.isoformat(), "fuels": out}
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/tools/ -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/octopus_mcp/tools/bill_summary.py src/octopus_mcp/tools/current_tariff.py tests/tools/test_bill_summary.py tests/tools/test_current_tariff.py
git commit -m "feat(tools): bill_summary and current_tariff thick tools"
```

---

### Task 20: Thick tools — `usage_breakdown` and `peak_hours`

**Files:**
- Create: `src/octopus_mcp/tools/usage_breakdown.py`
- Create: `src/octopus_mcp/tools/peak_hours.py`
- Create: `tests/tools/test_usage_breakdown.py`
- Create: `tests/tools/test_peak_hours.py`

- [ ] **Step 1: Write `tests/tools/test_usage_breakdown.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.analysis.aggregations import GroupBy
from octopus_mcp.cache.meters import MeterRow
from octopus_mcp.tools.period import PeriodSpec
from octopus_mcp.tools.usage_breakdown import usage_breakdown


class _R:
    def __init__(self, iso, kwh):
        self.interval_start = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        self.interval_end = self.interval_start
        self.consumption_kwh = kwh


@pytest.mark.asyncio
async def test_usage_breakdown_groups_by_day():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.list_meters_for_account.side_effect = lambda acct, fuel: (
        [MeterRow(account_number="A-1", fuel=fuel, mpan_or_mprn="m", serial_number="s")] if fuel == "electricity" else []
    )
    ctx.consumption_syncer.ensure = AsyncMock(return_value=[
        _R("2026-04-25T08:00:00Z", 1.0),
        _R("2026-04-25T20:00:00Z", 2.0),
        _R("2026-04-26T08:00:00Z", 0.5),
    ])

    out = await usage_breakdown(
        period=PeriodSpec(kind="last_7_days"),
        group_by="day",
        ctx=ctx,
        now=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    elec = out["fuel_breakdowns"]["electricity"]
    assert any(b["label"] == "2026-04-25" and b["kwh"] == 3.0 for b in elec)
    assert out["stats"]["electricity"]["mean"] > 0
```

- [ ] **Step 2: Write `tests/tools/test_peak_hours.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.cache.meters import MeterRow
from octopus_mcp.tools.peak_hours import peak_hours
from octopus_mcp.tools.period import PeriodSpec


class _R:
    def __init__(self, iso, kwh):
        self.interval_start = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        self.interval_end = self.interval_start
        self.consumption_kwh = kwh


@pytest.mark.asyncio
async def test_peak_hours_returns_top_n_per_fuel():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.list_meters_for_account.side_effect = lambda acct, fuel: (
        [MeterRow(account_number="A-1", fuel=fuel, mpan_or_mprn="m", serial_number="s")] if fuel == "electricity" else []
    )
    ctx.consumption_syncer.ensure = AsyncMock(return_value=[
        _R("2026-04-25T08:00:00Z", 1.0),
        _R("2026-04-25T18:00:00Z", 3.5),
        _R("2026-04-25T19:00:00Z", 2.7),
    ])
    out = await peak_hours(
        period=PeriodSpec(kind="last_7_days"),
        top_n=2,
        ctx=ctx,
        now=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    elec = out["fuels"]["electricity"]
    assert len(elec) == 2
    assert elec[0]["consumption_kwh"] == 3.5
```

- [ ] **Step 3: Run failing tests**

```bash
pytest tests/tools/test_usage_breakdown.py tests/tools/test_peak_hours.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/octopus_mcp/tools/usage_breakdown.py`**

```python
"""usage_breakdown thick tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from octopus_mcp.analysis.aggregations import GroupBy, aggregate, summary_stats
from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.tools.period import PeriodSpec, resolve_period

GroupByLiteral = Literal["hour", "day", "week", "month"]


async def usage_breakdown(
    *,
    period: PeriodSpec,
    group_by: GroupByLiteral = "day",
    ctx,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    period_from, period_to = resolve_period(period, now=now)
    gb = GroupBy(group_by)

    breakdowns: dict[str, list[dict[str, Any]]] = {}
    stats: dict[str, dict[str, float]] = {}

    for fuel in ("electricity", "gas"):
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=fuel)
        if not meters:
            continue
        meter = meters[0]
        rows = await ctx.consumption_syncer.ensure(
            fuel=fuel,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        points = [ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh) for r in rows]
        buckets = aggregate(points, group_by=gb)
        breakdowns[fuel] = [{"label": b.label, "kwh": b.kwh} for b in buckets]
        s = summary_stats([b.kwh for b in buckets])
        stats[fuel] = {"min": s.min, "max": s.max, "mean": s.mean, "stdev": s.stdev}

    return {
        "period": {"from": period_from.date().isoformat(), "to": period_to.date().isoformat()},
        "group_by": group_by,
        "fuel_breakdowns": breakdowns,
        "stats": stats,
    }
```

- [ ] **Step 5: Implement `src/octopus_mcp/tools/peak_hours.py`**

```python
"""peak_hours thick tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.analysis.peaks import top_n_half_hours
from octopus_mcp.tools.period import PeriodSpec, resolve_period


async def peak_hours(
    *,
    period: PeriodSpec,
    top_n: int = 10,
    ctx,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    period_from, period_to = resolve_period(period, now=now)

    out_fuels: dict[str, list[dict[str, Any]]] = {}
    for fuel in ("electricity", "gas"):
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=fuel)
        if not meters:
            continue
        meter = meters[0]
        rows = await ctx.consumption_syncer.ensure(
            fuel=fuel,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        points = [ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh) for r in rows]
        peaks = top_n_half_hours(points, n=top_n)
        out_fuels[fuel] = [
            {"interval_start": p.interval_start.isoformat(), "consumption_kwh": p.consumption_kwh}
            for p in peaks
        ]

    return {
        "period": {"from": period_from.date().isoformat(), "to": period_to.date().isoformat()},
        "top_n": top_n,
        "fuels": out_fuels,
    }
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/tools/ -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/octopus_mcp/tools/usage_breakdown.py src/octopus_mcp/tools/peak_hours.py tests/tools/test_usage_breakdown.py tests/tools/test_peak_hours.py
git commit -m "feat(tools): usage_breakdown and peak_hours thick tools"
```

---

### Task 21: Thick tool — `compare_tariff`

**Files:**
- Create: `src/octopus_mcp/tools/compare_tariff.py`
- Create: `tests/tools/test_compare_tariff.py`

- [ ] **Step 1: Write `tests/tools/test_compare_tariff.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.cache.meters import MeterRow, TariffAssignmentRow
from octopus_mcp.cache.rates import RateRow
from octopus_mcp.tools.compare_tariff import compare_tariff
from octopus_mcp.tools.period import PeriodSpec


class _R:
    def __init__(self, iso, kwh):
        self.interval_start = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        self.interval_end = self.interval_start
        self.consumption_kwh = kwh


@pytest.mark.asyncio
async def test_compare_tariff_returns_delta_and_caveats():
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.meters_repo.list_meters_for_account.side_effect = lambda acct, fuel: (
        [MeterRow(account_number="A-1", fuel=fuel, mpan_or_mprn="m", serial_number="s")] if fuel == "electricity" else []
    )
    ctx.meters_repo.current_tariff_assignment.return_value = TariffAssignmentRow(
        account_number="A-1", fuel="electricity", product_code="VAR-22-11-01", tariff_code="E-1R-CUR",
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None,
    )
    ctx.consumption_syncer.ensure = AsyncMock(return_value=[
        _R("2026-04-25T00:00:00Z", 1.0),
        _R("2026-04-25T12:00:00Z", 1.0),
    ])

    def _rates(tariff: str) -> list[RateRow]:
        v = 30.0 if tariff == "E-1R-CUR" else 20.0
        return [RateRow(valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=v, value_exc_vat=v)]

    def _sc(tariff: str) -> list[RateRow]:
        return [RateRow(valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc), valid_to=None, value_inc_vat=50.0, value_exc_vat=47.0)]

    ctx.rates_repo.get_unit_rates.side_effect = _rates
    ctx.rates_repo.get_standing_charges.side_effect = _sc

    async def _ensure_rates(*a, **k): return None
    ctx.ensure_rates = _ensure_rates

    # Provide a tariff lookup for the target product
    async def _resolve_target(product_code, fuel):
        return "E-1R-TGT"
    ctx.resolve_target_tariff_code = _resolve_target

    out = await compare_tariff(
        target_product_code="VAR-TARGET",
        period=PeriodSpec(kind="explicit", from_date=__import__("datetime").date(2026, 4, 25), to_date=__import__("datetime").date(2026, 4, 26)),
        fuel="both",
        ctx=ctx,
        now=datetime(2026, 4, 27, tzinfo=timezone.utc),
    )
    fc = out["fuels"][0]
    assert fc["fuel"] == "electricity"
    # 2 kWh * 30p = 60p + 50p = 110p current
    # 2 kWh * 20p = 40p + 50p = 90p target
    assert fc["delta_pence"] == -20
    assert any("Saving Sessions" in c for c in out["caveats"])
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/tools/test_compare_tariff.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/tools/compare_tariff.py`**

```python
"""compare_tariff thick tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from octopus_mcp.analysis.billing import ConsumptionPoint
from octopus_mcp.analysis.rate_lookup import RateStream, RateWindow
from octopus_mcp.analysis.tariff_comparison import FuelInputs, compare_tariffs
from octopus_mcp.octopus.errors import NotFoundError
from octopus_mcp.tools.period import PeriodSpec, resolve_period

FuelChoice = Literal["electricity", "gas", "both"]


def _windows(rows) -> list[RateWindow]:
    return [RateWindow(valid_from=r.valid_from, valid_to=r.valid_to, value_inc_vat=r.value_inc_vat) for r in rows]


def _intelligent_octopus_guard(target_product_code: str) -> None:
    if target_product_code.upper().startswith("INTELLI"):
        raise NotFoundError(
            "Intelligent Octopus comparison requires dispatch history not available without active enrolment. "
            "Try Cosy or Go for time-of-use comparison.",
            resource=target_product_code,
        )


async def compare_tariff(
    *,
    target_product_code: str,
    period: PeriodSpec,
    fuel: FuelChoice = "both",
    ctx,
    now: datetime | None = None,
) -> dict[str, Any]:
    _intelligent_octopus_guard(target_product_code)
    now = now or datetime.now(timezone.utc)
    period_from, period_to = resolve_period(period, now=now)

    fuels: list[FuelInputs] = []
    fuels_to_check = ("electricity", "gas") if fuel == "both" else (fuel,)

    for f in fuels_to_check:
        meters = ctx.meters_repo.list_meters_for_account(ctx.creds.account_number, fuel=f)
        if not meters:
            continue
        meter = meters[0]
        current = ctx.meters_repo.current_tariff_assignment(
            account_number=ctx.creds.account_number, fuel=f, at=period_from
        )
        if current is None:
            continue
        target_tariff = await ctx.resolve_target_tariff_code(target_product_code, f)

        await ctx.ensure_rates(product_code=current.product_code, tariff_code=current.tariff_code, fuel=f)
        await ctx.ensure_rates(product_code=target_product_code, tariff_code=target_tariff, fuel=f)

        rows = await ctx.consumption_syncer.ensure(
            fuel=f,
            mpan_or_mprn=meter.mpan_or_mprn,
            serial_number=meter.serial_number,
            period_from=period_from,
            period_to=period_to,
            now=now,
        )
        fuels.append(
            FuelInputs(
                fuel=f,  # type: ignore[arg-type]
                consumption=[ConsumptionPoint(interval_start=r.interval_start, consumption_kwh=r.consumption_kwh) for r in rows],
                current_unit_rates=RateStream(_windows(ctx.rates_repo.get_unit_rates(current.tariff_code))),
                current_standing=RateStream(_windows(ctx.rates_repo.get_standing_charges(current.tariff_code))),
                target_unit_rates=RateStream(_windows(ctx.rates_repo.get_unit_rates(target_tariff))),
                target_standing=RateStream(_windows(ctx.rates_repo.get_standing_charges(target_tariff))),
            )
        )

    if not fuels:
        raise NotFoundError("No fuels available to compare", resource="account")

    result = compare_tariffs(
        target_product_code=target_product_code,
        period_from=period_from,
        period_to=period_to,
        fuels=fuels,
    )
    return {
        "period": {"from": result.period[0].isoformat(), "to": result.period[1].isoformat()},
        "target_product_code": result.target_product_code,
        "fuels": [
            {
                "fuel": fc.fuel,
                "current_unit_pence": fc.current_unit_pence,
                "current_standing_pence": fc.current_standing_pence,
                "current_total_pence": fc.current_total_pence,
                "target_unit_pence": fc.target_unit_pence,
                "target_standing_pence": fc.target_standing_pence,
                "target_total_pence": fc.target_total_pence,
                "delta_pence": fc.delta_pence,
            }
            for fc in result.fuels
        ],
        "total_current_pence": result.total_current_pence,
        "total_target_pence": result.total_target_pence,
        "total_delta_pence": result.total_delta_pence,
        "pounds_summary": result.pounds_summary,
        "breakdown_by_day": [
            {"date": d.date.isoformat(), "current_pence": d.current_pence, "target_pence": d.target_pence, "delta_pence": d.delta_pence}
            for d in result.breakdown_by_day
        ],
        "caveats": result.caveats,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_compare_tariff.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/tools/compare_tariff.py tests/tools/test_compare_tariff.py
git commit -m "feat(tools): compare_tariff thick tool with intelligent-octopus guard"
```

---

### Task 22: Tool registration helpers + ensure_rates / target tariff resolver

**Files:**
- Modify: `src/octopus_mcp/tools/context.py` (add `ensure_rates`, `resolve_target_tariff_code`, `bootstrap`)
- Create: `tests/tools/test_context_helpers.py`

- [ ] **Step 1: Write `tests/tools/test_context_helpers.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.meters import MetersRepo, TariffAssignmentRow
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.tools.context import ToolContext, build_helpers


@pytest.mark.asyncio
async def test_ensure_rates_calls_rest_then_caches():
    conn = open_db(":memory:")
    rates_repo = RatesRepo(conn)
    rest = AsyncMock()

    class _Rate:
        def __init__(self, vf, vi):
            self.valid_from, self.valid_to, self.value_inc_vat, self.value_exc_vat = vf, None, vi, vi - 1

    rest.get_electricity_unit_rates.return_value = [_Rate(datetime(2026, 4, 1, tzinfo=timezone.utc), 25.0)]
    rest.get_electricity_standing_charges.return_value = [_Rate(datetime(2026, 4, 1, tzinfo=timezone.utc), 50.0)]

    ctx = MagicMock()
    ctx.rest = rest
    ctx.rates_repo = rates_repo
    ctx.sync_state = MagicMock()
    ctx.sync_state.is_fresh.return_value = False

    helpers = build_helpers(ctx)

    await helpers.ensure_rates(product_code="VAR-22-11-01", tariff_code="E-1R-VAR-22-11-01-A", fuel="electricity")
    rows = rates_repo.get_unit_rates("E-1R-VAR-22-11-01-A")
    assert rows and rows[0].value_inc_vat == 25.0
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/tools/test_context_helpers.py -v
```

Expected: ImportError on `build_helpers`.

- [ ] **Step 3: Extend `src/octopus_mcp/tools/context.py`**

Append to the existing file:

```python
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class _Helpers:
    ensure_rates: object
    resolve_target_tariff_code: object


def build_helpers(ctx) -> _Helpers:
    """Attaches `ensure_rates` and `resolve_target_tariff_code` async closures to the context."""

    async def ensure_rates(*, product_code: str, tariff_code: str, fuel: str) -> None:
        key = f"rates:{fuel}:{tariff_code}"
        now = datetime.now(timezone.utc)
        if ctx.sync_state.is_fresh(key, now=now):
            return
        if fuel == "electricity":
            unit_rows = await ctx.rest.get_electricity_unit_rates(product_code, tariff_code)
            sc_rows = await ctx.rest.get_electricity_standing_charges(product_code, tariff_code)
        else:
            unit_rows = await ctx.rest.get_gas_unit_rates(product_code, tariff_code)
            sc_rows = await ctx.rest.get_gas_standing_charges(product_code, tariff_code)
        from octopus_mcp.cache.rates import RateRow

        ctx.rates_repo.upsert_unit_rates(
            tariff_code=tariff_code,
            fuel=fuel,
            rows=[RateRow(valid_from=r.valid_from, valid_to=r.valid_to, value_inc_vat=r.value_inc_vat, value_exc_vat=r.value_exc_vat) for r in unit_rows],
        )
        ctx.rates_repo.upsert_standing_charges(
            tariff_code=tariff_code,
            fuel=fuel,
            rows=[RateRow(valid_from=r.valid_from, valid_to=r.valid_to, value_inc_vat=r.value_inc_vat, value_exc_vat=r.value_exc_vat) for r in sc_rows],
        )
        ctx.sync_state.touch(key, at=now, ttl_seconds=86400)

    async def resolve_target_tariff_code(product_code: str, fuel: str) -> str:
        """Pick the user's region-appropriate tariff code from a target product."""
        from octopus_mcp.octopus.errors import NotFoundError

        product = await ctx.rest.get_product(product_code)
        section_key = "single_register_electricity_tariffs" if fuel == "electricity" else "single_register_gas_tariffs"
        section = product.get(section_key, {})
        if not section:
            raise NotFoundError(
                f"Product {product_code} has no {fuel} tariffs",
                resource=product_code,
            )
        # Use first region; in v2 we pick by user's region.
        first_region = next(iter(section.values()))
        if "direct_debit_monthly" in first_region:
            return first_region["direct_debit_monthly"]["code"]
        if "direct_debit_quarterly" in first_region:
            return first_region["direct_debit_quarterly"]["code"]
        # fallback: any code
        for variant in first_region.values():
            if "code" in variant:
                return variant["code"]
        raise NotFoundError(f"No tariff code found in product {product_code}", resource=product_code)

    ctx.ensure_rates = ensure_rates
    ctx.resolve_target_tariff_code = resolve_target_tariff_code
    return _Helpers(ensure_rates=ensure_rates, resolve_target_tariff_code=resolve_target_tariff_code)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_context_helpers.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/tools/context.py tests/tools/test_context_helpers.py
git commit -m "feat(tools): ensure_rates and target-tariff resolver helpers on context"
```

---

## Phase 5 — MCP server + CLI

### Task 23: MCP server entrypoint with tool registration

**Files:**
- Create: `src/octopus_mcp/server.py`
- Create: `src/octopus_mcp/logging_setup.py`
- Create: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

`tests/test_server.py`:
```python
import pytest

from octopus_mcp.server import _build_app


def test_build_app_registers_expected_tools():
    app, _ = _build_app(test_mode=True)
    names = {t.name for t in app.list_tools_sync()}
    expected = {
        "bill_summary",
        "current_tariff",
        "usage_breakdown",
        "peak_hours",
        "compare_tariff",
        "get_account",
        "list_products",
        "get_product",
        "get_consumption_raw",
    }
    assert expected.issubset(names)
```

Note: depending on the MCP SDK version, `list_tools_sync` may not exist. The test is illustrative — adapt to the actual API surface during implementation. If the SDK exposes `app.tools` or requires `await app.list_tools()`, switch to that. The intent is: assert the registered tool names cover the expected set.

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_server.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/logging_setup.py`**

```python
"""Stderr JSON logging with secret redaction."""

from __future__ import annotations

import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir

_REDACT_KEYS = {"authorization", "api_key", "password", "token", "jwt"}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in payload or k.startswith("_") or k in {"args", "msg", "exc_info", "exc_text", "stack_info", "stack_level"}:
                continue
            if k.lower() in _REDACT_KEYS:
                payload[k] = "***"
            elif isinstance(v, (str, int, float, bool)) or v is None:
                payload[k] = v
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None) -> None:
    level_name = (level or os.environ.get("OCTOPUS_MCP_LOG_LEVEL") or "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level_name)

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(_JsonFormatter())
    root.handlers = [stderr]

    log_dir = Path(user_log_dir("octopus-mcp"))
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(log_dir / "server.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setFormatter(_JsonFormatter())
    root.addHandler(fh)
```

- [ ] **Step 4: Implement `src/octopus_mcp/server.py`**

```python
"""MCP server entrypoint."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from platformdirs import user_cache_dir
from pydantic import BaseModel, Field

from octopus_mcp.cache.consumption import ConsumptionRepo
from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.meters import MetersRepo
from octopus_mcp.cache.products import ProductsRepo
from octopus_mcp.cache.rates import RatesRepo
from octopus_mcp.cache.sync import ConsumptionSyncer
from octopus_mcp.cache.sync_state import SyncStateRepo
from octopus_mcp.logging_setup import configure_logging
from octopus_mcp.octopus.auth import resolve_credentials
from octopus_mcp.octopus.errors import OctopusError
from octopus_mcp.octopus.rest import OctopusRestClient
from octopus_mcp.tools.bill_summary import bill_summary
from octopus_mcp.tools.compare_tariff import compare_tariff
from octopus_mcp.tools.context import ToolContext, build_helpers
from octopus_mcp.tools.current_tariff import current_tariff
from octopus_mcp.tools.peak_hours import peak_hours
from octopus_mcp.tools.period import PeriodSpec
from octopus_mcp.tools.thin import (
    get_account,
    get_consumption_raw,
    get_product,
    list_products,
)
from octopus_mcp.tools.usage_breakdown import usage_breakdown


class PeriodArg(BaseModel):
    kind: str = Field(..., description="last_month | last_7_days | last_quarter | ytd | explicit")
    from_date: date | None = None
    to_date: date | None = None

    def to_spec(self) -> PeriodSpec:
        return PeriodSpec(kind=self.kind, from_date=self.from_date, to_date=self.to_date)  # type: ignore[arg-type]


def _cache_path() -> Path:
    base = Path(user_cache_dir("octopus-mcp"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "cache.db"


def _build_app(*, test_mode: bool = False) -> tuple[FastMCP, ToolContext | None]:
    app = FastMCP("octopus-mcp")

    if test_mode:
        ctx: ToolContext | None = None
    else:
        creds = resolve_credentials()
        conn = open_db(str(_cache_path()))
        rest = OctopusRestClient(creds)
        consumption_repo = ConsumptionRepo(conn)
        rates_repo = RatesRepo(conn)
        meters_repo = MetersRepo(conn)
        products_repo = ProductsRepo(conn)
        sync_state = SyncStateRepo(conn)
        ctx = ToolContext(
            creds=creds,
            rest=rest,
            conn=conn,
            consumption_repo=consumption_repo,
            rates_repo=rates_repo,
            meters_repo=meters_repo,
            products_repo=products_repo,
            sync_state=sync_state,
            consumption_syncer=ConsumptionSyncer(rest=rest, repo=consumption_repo, state=sync_state),
        )
        build_helpers(ctx)

    def _wrap(coro_factory):
        async def runner(**kw):
            if ctx is None:
                raise RuntimeError("Server initialised in test_mode without ToolContext")
            try:
                return await coro_factory(ctx=ctx, **kw)
            except OctopusError as e:
                return {
                    "code": type(e).__name__,
                    "message": str(e),
                    "retryable": isinstance(e, __import__("octopus_mcp.octopus.errors", fromlist=["RateLimitError"]).RateLimitError),
                }

        return runner

    @app.tool(name="bill_summary", description="Total cost (£/pence) per fuel for a period")
    async def _bill_summary(period: PeriodArg) -> dict[str, Any]:
        return await _wrap(lambda ctx: bill_summary(period=period.to_spec(), ctx=ctx))()

    @app.tool(name="current_tariff", description="Currently active tariff per fuel")
    async def _current_tariff() -> dict[str, Any]:
        return await _wrap(lambda ctx: current_tariff(ctx=ctx))()

    @app.tool(name="usage_breakdown", description="Aggregated kWh by hour/day/week/month")
    async def _usage_breakdown(period: PeriodArg, group_by: str = "day") -> dict[str, Any]:
        return await _wrap(lambda ctx: usage_breakdown(period=period.to_spec(), group_by=group_by, ctx=ctx))()

    @app.tool(name="peak_hours", description="Top-N highest-usage half-hours")
    async def _peak_hours(period: PeriodArg, top_n: int = 10) -> dict[str, Any]:
        return await _wrap(lambda ctx: peak_hours(period=period.to_spec(), top_n=top_n, ctx=ctx))()

    @app.tool(name="compare_tariff", description="Replay actual usage against another Octopus tariff")
    async def _compare_tariff(target_product_code: str, period: PeriodArg, fuel: str = "both") -> dict[str, Any]:
        return await _wrap(lambda ctx: compare_tariff(target_product_code=target_product_code, period=period.to_spec(), fuel=fuel, ctx=ctx))()  # type: ignore[arg-type]

    @app.tool(name="get_account", description="Account details + meters + tariff history")
    async def _get_account() -> dict[str, Any]:
        return await _wrap(lambda ctx: get_account(rest=ctx.rest))()

    @app.tool(name="list_products", description="Browse Octopus product catalogue")
    async def _list_products() -> list[dict[str, Any]]:
        return await _wrap(lambda ctx: list_products(rest=ctx.rest))()

    @app.tool(name="get_product", description="Detail for one product code")
    async def _get_product(code: str) -> dict[str, Any]:
        return await _wrap(lambda ctx: get_product(code, rest=ctx.rest))()

    @app.tool(name="get_consumption_raw", description="Half-hourly consumption rows for a meter")
    async def _get_consumption_raw(
        fuel: str, mpan_or_mprn: str, serial_number: str, period_from: str, period_to: str
    ) -> list[dict[str, Any]]:
        from datetime import datetime as _dt
        return await _wrap(
            lambda ctx: get_consumption_raw(
                fuel=fuel,
                mpan_or_mprn=mpan_or_mprn,
                serial_number=serial_number,
                period_from=_dt.fromisoformat(period_from),
                period_to=_dt.fromisoformat(period_to),
                rest=ctx.rest,
            )
        )()

    return app, ctx


def run() -> int:
    configure_logging()
    app, _ = _build_app()
    asyncio.run(app.run_stdio())
    return 0
```

Note: `mcp.server.fastmcp.FastMCP` API names (`tool`, `run_stdio`, `list_tools_sync`) reflect the SDK at the time of writing. The implementer should adjust to whatever the installed SDK version exposes — the *shape* (decorate, register, run over stdio) is stable.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_server.py -v
```

Expected: PASS (after any SDK-API tweaks).

- [ ] **Step 6: Commit**

```bash
git add src/octopus_mcp/server.py src/octopus_mcp/logging_setup.py tests/test_server.py
git commit -m "feat(server): MCP entrypoint with tool registration and JSON logging"
```

---

### Task 24: CLI subcommands (`serve`, `configure`, `resync`, `version`)

**Files:**
- Modify: `src/octopus_mcp/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
import sys

import pytest

from octopus_mcp import __version__
from octopus_mcp.cli import build_parser, main


def test_version_subcommand_prints_version(capsys):
    parser = build_parser()
    args = parser.parse_args(["version"])
    args.func(args)
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_lists_subcommands(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    out = capsys.readouterr().out
    for cmd in ("serve", "configure", "resync", "version"):
        assert cmd in out


def test_main_with_no_args_invokes_serve(monkeypatch):
    called = {"served": False}

    def fake_run() -> int:
        called["served"] = True
        return 0

    monkeypatch.setattr("octopus_mcp.cli._run_serve", fake_run)
    monkeypatch.setattr(sys, "argv", ["octopus-mcp"])
    rc = main()
    assert rc == 0 and called["served"]
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL on `build_parser` import.

- [ ] **Step 3: Implement `src/octopus_mcp/cli.py`**

```python
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
    from platformdirs import user_cache_dir

    db_path = Path(user_cache_dir("octopus-mcp")) / "cache.db"
    if not db_path.exists():
        print(f"No cache at {db_path}; nothing to do.")
        return 0

    import sqlite3

    conn = sqlite3.connect(db_path)
    if args.resource == "all":
        for tbl in ("consumption", "unit_rates", "standing_charges", "products", "saving_sessions", "octoplus_events", "sync_state"):
            conn.execute(f"DELETE FROM {tbl}")
    elif args.resource == "consumption":
        conn.execute("DELETE FROM consumption")
        conn.execute("DELETE FROM sync_state WHERE resource LIKE 'consumption:%'")
    else:
        print(f"Unknown resource: {args.resource}", file=sys.stderr)
        return 1
    conn.commit()
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cli.py -v
```

Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/cli.py tests/test_cli.py
git commit -m "feat(cli): serve/configure/resync/version subcommands"
```

---

### Task 25: End-to-end smoke test (subprocess JSON-RPC)

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/test_stdio_smoke.py`

- [ ] **Step 1: Write the test**

`tests/e2e/test_stdio_smoke.py`:
```python
"""Boot the MCP server in a subprocess and ensure it responds to a list_tools request.

Skipped if the MCP SDK isn't importable in test_mode wiring. This test is intentionally
shallow — it proves the binary launches and speaks the protocol; deeper behaviour is
tested at the tool/unit level.
"""

import json
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.timeout(15)


def test_server_responds_to_list_tools(tmp_path, monkeypatch):
    monkeypatch.setenv("OCTOPUS_API_KEY", "sk_test")
    monkeypatch.setenv("OCTOPUS_ACCOUNT_NUMBER", "A-TEST")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    proc = subprocess.Popen(
        [sys.executable, "-m", "octopus_mcp.cli", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ},
        text=True,
    )
    try:
        # MCP initialize handshake
        initialize = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}},
        }
        proc.stdin.write(json.dumps(initialize) + "\n")
        proc.stdin.flush()
        resp_line = proc.stdout.readline()
        resp = json.loads(resp_line)
        assert resp["id"] == 1
        assert "result" in resp

        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        proc.stdin.write(json.dumps(list_req) + "\n")
        proc.stdin.flush()
        list_resp = json.loads(proc.stdout.readline())
        names = {t["name"] for t in list_resp["result"]["tools"]}
        for n in ("bill_summary", "compare_tariff", "current_tariff"):
            assert n in names
    finally:
        proc.terminate()
        proc.wait(timeout=5)
```

Note: This depends on `python -m octopus_mcp.cli` being runnable. Add a `__main__.py` if needed:

`src/octopus_mcp/__main__.py`:
```python
from octopus_mcp.cli import main
import sys
sys.exit(main())
```

- [ ] **Step 2: Add `pytest-timeout` if not present**

```bash
uv pip install pytest-timeout
```

(And add `pytest-timeout` to `[project.optional-dependencies].dev` in `pyproject.toml`.)

- [ ] **Step 3: Run the smoke test**

```bash
pytest tests/e2e/ -v
```

Expected: PASS. If MCP SDK protocol handshake differs slightly, adjust `initialize` params to match the version pinned.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/ src/octopus_mcp/__main__.py pyproject.toml
git commit -m "test(e2e): subprocess JSON-RPC smoke test for MCP server"
```

---

## CHECKPOINT — MVP COMPLETE (Phases 0–5)

You now have a working MCP server with all REST-only tools (`bill_summary`, `current_tariff`, `usage_breakdown`, `peak_hours`, `compare_tariff`, plus the thin getters), an installable CLI with `serve`/`configure`/`resync`/`version`, and a smoke test that proves it boots and responds to JSON-RPC.

What's missing from the v1 spec: Kraken-backed `saving_session_history` + `kraken_query` escape hatch, the Claude Code plugin (manifest + slash commands + skill), and the release pipeline. Those are Phases 6 and 7.

---

## Phase 6 — Kraken GraphQL (Saving Sessions, Octoplus)

### Task 26: Kraken client with JWT mint and refresh

**Files:**
- Create: `src/octopus_mcp/octopus/kraken.py`
- Create: `tests/octopus/test_kraken.py`

- [ ] **Step 1: Write the failing test**

`tests/octopus/test_kraken.py`:
```python
import httpx
import pytest

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import AuthenticationError
from octopus_mcp.octopus.kraken import KrakenClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport, base_url="https://api.octopus.energy")
    return KrakenClient(
        OctopusCredentials(api_key="sk_test", account_number="A-1"),
        http_client=http,
    )


@pytest.mark.asyncio
async def test_first_call_mints_jwt_and_uses_it():
    calls = {"mints": 0, "queries": 0}
    last_auth = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            calls["mints"] += 1
            return httpx.Response(200, json={"data": {"obtainKrakenToken": {"token": "JWT-FAKE"}}})
        calls["queries"] += 1
        last_auth["v"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": {"viewer": {"id": "vid"}}})

    async with _client(handler) as kc:
        out = await kc.query("query { viewer { id } }")
    assert calls["mints"] == 1
    assert calls["queries"] == 1
    assert out == {"viewer": {"id": "vid"}}
    assert last_auth["v"] == "JWT JWT-FAKE"


@pytest.mark.asyncio
async def test_unauthenticated_response_triggers_one_remint_then_retry():
    state = {"phase": 0, "mints": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            state["mints"] += 1
            return httpx.Response(200, json={"data": {"obtainKrakenToken": {"token": f"T{state['mints']}"}}})
        state["phase"] += 1
        if state["phase"] == 1:
            return httpx.Response(200, json={"errors": [{"extensions": {"errorCode": "KT-CT-1124"}, "message": "unauthorised"}]})
        return httpx.Response(200, json={"data": {"viewer": {"id": "ok"}}})

    async with _client(handler) as kc:
        out = await kc.query("query { viewer { id } }")
    assert out == {"viewer": {"id": "ok"}}
    assert state["mints"] == 2  # initial mint + remint after 1124


@pytest.mark.asyncio
async def test_persistent_auth_failure_raises_authentication_error():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        if "obtainKrakenToken" in body:
            return httpx.Response(200, json={"data": {"obtainKrakenToken": {"token": "T"}}})
        return httpx.Response(200, json={"errors": [{"extensions": {"errorCode": "KT-CT-1124"}, "message": "no"}]})

    async with _client(handler) as kc:
        with pytest.raises(AuthenticationError):
            await kc.query("query {}")
```

- [ ] **Step 2: Run failing test**

```bash
pytest tests/octopus/test_kraken.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `src/octopus_mcp/octopus/kraken.py`**

```python
"""Kraken GraphQL client with JWT lifecycle.

The token is short-lived (~1h). We mint on first use and remint exactly once
on an unauthenticated response, then surface the error.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from octopus_mcp.octopus.auth import OctopusCredentials
from octopus_mcp.octopus.errors import AuthenticationError, DataError, ServiceError

_GRAPHQL_PATH = "/v1/graphql/"
_AUTH_ERROR_CODES = {"KT-CT-1124", "KT-CT-1139", "KT-CT-1112"}  # known Kraken auth errors

_log = logging.getLogger(__name__)

_OBTAIN_TOKEN_MUTATION = """
mutation ObtainToken($apiKey: String!) {
  obtainKrakenToken(input: { APIKey: $apiKey }) {
    token
  }
}
"""


class KrakenClient:
    def __init__(
        self,
        credentials: OctopusCredentials,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._creds = credentials
        self._token: str | None = None
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url="https://api.octopus.energy", timeout=httpx.Timeout(30.0)
        )

    async def __aenter__(self) -> "KrakenClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def _mint_token(self) -> str:
        resp = await self._http.post(
            _GRAPHQL_PATH,
            json={"query": _OBTAIN_TOKEN_MUTATION, "variables": {"apiKey": self._creds.api_key}},
        )
        if resp.status_code >= 500:
            raise ServiceError(f"Kraken auth upstream error {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as e:
            raise DataError("Kraken returned non-JSON during auth", raw_excerpt=resp.text) from e
        if "errors" in data:
            raise AuthenticationError(f"Kraken refused to mint token: {data['errors']}")
        token = data.get("data", {}).get("obtainKrakenToken", {}).get("token")
        if not token:
            raise DataError("Kraken auth response missing token", raw_excerpt=resp.text)
        return token

    async def query(self, document: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._token is None:
            self._token = await self._mint_token()

        for attempt in range(2):
            resp = await self._http.post(
                _GRAPHQL_PATH,
                json={"query": document, "variables": variables or {}},
                headers={"Authorization": f"JWT {self._token}"},
            )
            if resp.status_code >= 500:
                raise ServiceError(f"Kraken upstream {resp.status_code}")
            try:
                payload = resp.json()
            except ValueError as e:
                raise DataError("Kraken returned non-JSON", raw_excerpt=resp.text) from e

            if "errors" in payload:
                codes = {
                    (e.get("extensions") or {}).get("errorCode")
                    for e in payload["errors"]
                }
                if codes & _AUTH_ERROR_CODES and attempt == 0:
                    self._token = await self._mint_token()
                    continue
                if codes & _AUTH_ERROR_CODES:
                    raise AuthenticationError(f"Kraken auth failed after retry: {payload['errors']}")
                raise DataError(f"Kraken returned errors: {payload['errors']}")
            return payload.get("data", {})
        raise AuthenticationError("Kraken auth failed after retry")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/octopus/test_kraken.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/octopus_mcp/octopus/kraken.py tests/octopus/test_kraken.py
git commit -m "feat(kraken): GraphQL client with JWT mint and one-shot refresh on auth failure"
```

---

### Task 27: Saving Sessions and Octoplus queries + cache

**Files:**
- Create: `src/octopus_mcp/octopus/kraken_queries.py`
- Create: `src/octopus_mcp/cache/kraken_repo.py`
- Create: `tests/octopus/test_kraken_queries.py`
- Create: `tests/cache/test_kraken_repo.py`

- [ ] **Step 1: Write `tests/cache/test_kraken_repo.py`**

```python
from datetime import datetime, timezone

from octopus_mcp.cache.db import open_db
from octopus_mcp.cache.kraken_repo import (
    KrakenRepo,
    OctoplusEventRow,
    SavingSessionRow,
)


def test_upsert_and_list_saving_sessions():
    repo = KrakenRepo(open_db(":memory:"))
    repo.upsert_saving_sessions([
        SavingSessionRow(
            id="ss-1",
            code="SS-2026-01",
            starts_at=datetime(2026, 1, 12, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 1, 12, 18, 30, tzinfo=timezone.utc),
            points_awarded=400,
            kwh_saved=1.7,
            joined=True,
        )
    ])
    rows = repo.list_saving_sessions()
    assert rows[0].id == "ss-1"
    assert rows[0].joined is True


def test_upsert_and_list_octoplus_events():
    repo = KrakenRepo(open_db(":memory:"))
    repo.upsert_octoplus_events([
        OctoplusEventRow(
            id="ev-1",
            event_type="POINTS_AWARDED",
            points=400,
            occurred_at=datetime(2026, 1, 12, tzinfo=timezone.utc),
            payload={"reason": "saving session"},
        )
    ])
    rows = repo.list_octoplus_events()
    assert rows[0].points == 400
```

- [ ] **Step 2: Write `tests/octopus/test_kraken_queries.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from octopus_mcp.octopus.kraken_queries import (
    fetch_octoplus_events,
    fetch_saving_sessions,
)


@pytest.mark.asyncio
async def test_fetch_saving_sessions_parses_response():
    kraken = AsyncMock()
    kraken.query.return_value = {
        "savingSessions": {
            "events": [
                {
                    "id": "ss-1",
                    "code": "SS-2026-01",
                    "startAt": "2026-01-12T17:00:00Z",
                    "endAt": "2026-01-12T18:30:00Z",
                    "octopoints": 400,
                    "kwhSaved": "1.7",
                    "joined": True,
                }
            ]
        }
    }
    rows = await fetch_saving_sessions(kraken=kraken, account_number="A-1")
    assert len(rows) == 1
    assert rows[0].id == "ss-1"
    assert rows[0].kwh_saved == 1.7
    assert rows[0].joined is True


@pytest.mark.asyncio
async def test_fetch_octoplus_events_parses_response():
    kraken = AsyncMock()
    kraken.query.return_value = {
        "octoplusAccountInfo": {
            "events": [
                {"id": "ev-1", "type": "POINTS_AWARDED", "points": 400, "occurredAt": "2026-01-12T00:00:00Z", "metadata": {"reason": "x"}}
            ]
        }
    }
    rows = await fetch_octoplus_events(kraken=kraken, account_number="A-1")
    assert rows[0].points == 400
```

- [ ] **Step 3: Run failing tests**

```bash
pytest tests/cache/test_kraken_repo.py tests/octopus/test_kraken_queries.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement `src/octopus_mcp/cache/kraken_repo.py`**

```python
"""Repository for Kraken-sourced data (saving sessions, octoplus events)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass(frozen=True)
class SavingSessionRow:
    id: str
    code: str | None
    starts_at: datetime
    ends_at: datetime
    points_awarded: int | None
    kwh_saved: float | None
    joined: bool


@dataclass(frozen=True)
class OctoplusEventRow:
    id: str
    event_type: str
    points: int | None
    occurred_at: datetime
    payload: dict[str, Any]


class KrakenRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert_saving_sessions(self, rows: list[SavingSessionRow]) -> None:
        self._conn.executemany(
            """
            INSERT INTO saving_sessions (id, code, starts_at, ends_at, points_awarded, kwh_saved, joined)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              code=excluded.code,
              starts_at=excluded.starts_at,
              ends_at=excluded.ends_at,
              points_awarded=excluded.points_awarded,
              kwh_saved=excluded.kwh_saved,
              joined=excluded.joined
            """,
            [
                (r.id, r.code, _iso(r.starts_at), _iso(r.ends_at), r.points_awarded, r.kwh_saved, int(r.joined))
                for r in rows
            ],
        )

    def list_saving_sessions(self) -> list[SavingSessionRow]:
        rs = self._conn.execute("SELECT * FROM saving_sessions ORDER BY starts_at").fetchall()
        return [
            SavingSessionRow(
                id=r["id"],
                code=r["code"],
                starts_at=_parse(r["starts_at"]),
                ends_at=_parse(r["ends_at"]),
                points_awarded=r["points_awarded"],
                kwh_saved=r["kwh_saved"],
                joined=bool(r["joined"]),
            )
            for r in rs
        ]

    def upsert_octoplus_events(self, rows: list[OctoplusEventRow]) -> None:
        self._conn.executemany(
            """
            INSERT INTO octoplus_events (id, event_type, points, occurred_at, payload_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              event_type=excluded.event_type,
              points=excluded.points,
              occurred_at=excluded.occurred_at,
              payload_json=excluded.payload_json
            """,
            [(r.id, r.event_type, r.points, _iso(r.occurred_at), json.dumps(r.payload)) for r in rows],
        )

    def list_octoplus_events(self) -> list[OctoplusEventRow]:
        rs = self._conn.execute("SELECT * FROM octoplus_events ORDER BY occurred_at").fetchall()
        return [
            OctoplusEventRow(
                id=r["id"],
                event_type=r["event_type"],
                points=r["points"],
                occurred_at=_parse(r["occurred_at"]),
                payload=json.loads(r["payload_json"]),
            )
            for r in rs
        ]
```

- [ ] **Step 5: Implement `src/octopus_mcp/octopus/kraken_queries.py`**

```python
"""Concrete Kraken queries used by the MCP."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from octopus_mcp.cache.kraken_repo import OctoplusEventRow, SavingSessionRow


_SAVING_SESSIONS_QUERY = """
query SavingSessions($acct: String!) {
  savingSessions(accountNumber: $acct) {
    events {
      id code startAt endAt octopoints kwhSaved joined
    }
  }
}
"""

_OCTOPLUS_QUERY = """
query OctoplusEvents($acct: String!) {
  octoplusAccountInfo(accountNumber: $acct) {
    events {
      id type points occurredAt metadata
    }
  }
}
"""


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


async def fetch_saving_sessions(*, kraken, account_number: str) -> list[SavingSessionRow]:
    data = await kraken.query(_SAVING_SESSIONS_QUERY, {"acct": account_number})
    events = (data.get("savingSessions") or {}).get("events") or []
    out: list[SavingSessionRow] = []
    for e in events:
        out.append(
            SavingSessionRow(
                id=str(e["id"]),
                code=e.get("code"),
                starts_at=_parse_dt(e["startAt"]),
                ends_at=_parse_dt(e["endAt"]),
                points_awarded=e.get("octopoints"),
                kwh_saved=float(e["kwhSaved"]) if e.get("kwhSaved") is not None else None,
                joined=bool(e.get("joined", False)),
            )
        )
    return out


async def fetch_octoplus_events(*, kraken, account_number: str) -> list[OctoplusEventRow]:
    data = await kraken.query(_OCTOPLUS_QUERY, {"acct": account_number})
    events = (data.get("octoplusAccountInfo") or {}).get("events") or []
    return [
        OctoplusEventRow(
            id=str(e["id"]),
            event_type=str(e["type"]),
            points=e.get("points"),
            occurred_at=_parse_dt(e["occurredAt"]),
            payload=e.get("metadata") or {},
        )
        for e in events
    ]
```

Note: Kraken's GraphQL schema for these specific queries is community-discovered and may need tweaking based on what the live API actually exposes. The tests cover the parsing logic against a documented response shape; if the field names differ in production (e.g., `octopoints` vs `points`), update the queries and parser without re-architecting.

- [ ] **Step 6: Run tests**

```bash
pytest tests/cache/test_kraken_repo.py tests/octopus/test_kraken_queries.py -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/octopus_mcp/cache/kraken_repo.py src/octopus_mcp/octopus/kraken_queries.py tests/cache/test_kraken_repo.py tests/octopus/test_kraken_queries.py
git commit -m "feat(kraken): saving-sessions and octoplus-events queries + repository"
```

---

### Task 28: `saving_session_history` tool + `kraken_query` escape hatch + server registration

**Files:**
- Create: `src/octopus_mcp/tools/saving_sessions.py`
- Create: `src/octopus_mcp/tools/kraken_passthrough.py`
- Modify: `src/octopus_mcp/tools/context.py` (add `kraken: KrakenClient` and `kraken_repo: KrakenRepo`)
- Modify: `src/octopus_mcp/server.py` (wire kraken into context, register two new tools)
- Create: `tests/tools/test_saving_sessions.py`

- [ ] **Step 1: Write `tests/tools/test_saving_sessions.py`**

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from octopus_mcp.cache.kraken_repo import OctoplusEventRow, SavingSessionRow
from octopus_mcp.tools.saving_sessions import saving_session_history


@pytest.mark.asyncio
async def test_saving_session_history_returns_combined_view(monkeypatch):
    ctx = MagicMock()
    ctx.creds.account_number = "A-1"
    ctx.kraken_repo.list_saving_sessions.return_value = [
        SavingSessionRow(
            id="ss-1", code="SS-2026-01",
            starts_at=datetime(2026, 1, 12, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 1, 12, 18, 30, tzinfo=timezone.utc),
            points_awarded=400, kwh_saved=1.7, joined=True,
        )
    ]
    ctx.kraken_repo.list_octoplus_events.return_value = [
        OctoplusEventRow(id="ev-1", event_type="POINTS_AWARDED", points=400, occurred_at=datetime(2026, 1, 12, tzinfo=timezone.utc), payload={})
    ]

    async def _ensure_kraken_synced(): return None
    ctx.ensure_kraken_synced = _ensure_kraken_synced

    out = await saving_session_history(ctx=ctx)
    assert len(out["sessions"]) == 1
    assert out["totals"]["points_awarded"] == 400
    assert out["totals"]["sessions_joined"] == 1
```

- [ ] **Step 2: Implement `src/octopus_mcp/tools/saving_sessions.py`**

```python
"""saving_session_history thick tool."""

from __future__ import annotations

from typing import Any


async def saving_session_history(*, ctx) -> dict[str, Any]:
    await ctx.ensure_kraken_synced()
    sessions = ctx.kraken_repo.list_saving_sessions()
    events = ctx.kraken_repo.list_octoplus_events()

    points_total = sum(s.points_awarded or 0 for s in sessions if s.joined)
    kwh_total = sum(s.kwh_saved or 0.0 for s in sessions if s.joined)

    return {
        "sessions": [
            {
                "id": s.id,
                "code": s.code,
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "joined": s.joined,
                "points_awarded": s.points_awarded,
                "kwh_saved": s.kwh_saved,
            }
            for s in sessions
        ],
        "octoplus_events": [
            {
                "id": e.id,
                "type": e.event_type,
                "points": e.points,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "totals": {
            "sessions_total": len(sessions),
            "sessions_joined": sum(1 for s in sessions if s.joined),
            "points_awarded": points_total,
            "kwh_saved": round(kwh_total, 3),
        },
    }
```

- [ ] **Step 3: Implement `src/octopus_mcp/tools/kraken_passthrough.py`**

```python
"""kraken_query escape hatch for ad-hoc GraphQL."""

from __future__ import annotations

from typing import Any


async def kraken_query(query: str, variables: dict[str, Any] | None = None, *, ctx) -> dict[str, Any]:
    return await ctx.kraken.query(query, variables or {})
```

- [ ] **Step 4: Extend `src/octopus_mcp/tools/context.py`**

Add to `ToolContext` dataclass:

```python
    kraken: object | None = None        # KrakenClient
    kraken_repo: object | None = None   # KrakenRepo
```

Append a sync helper to `build_helpers`:

```python
    async def ensure_kraken_synced() -> None:
        from datetime import datetime, timezone
        from octopus_mcp.octopus.kraken_queries import fetch_octoplus_events, fetch_saving_sessions

        key = f"kraken:{ctx.creds.account_number}"
        now = datetime.now(timezone.utc)
        if ctx.sync_state.is_fresh(key, now=now):
            return
        sessions = await fetch_saving_sessions(kraken=ctx.kraken, account_number=ctx.creds.account_number)
        events = await fetch_octoplus_events(kraken=ctx.kraken, account_number=ctx.creds.account_number)
        ctx.kraken_repo.upsert_saving_sessions(sessions)
        ctx.kraken_repo.upsert_octoplus_events(events)
        ctx.sync_state.touch(key, at=now, ttl_seconds=3600)

    ctx.ensure_kraken_synced = ensure_kraken_synced
```

- [ ] **Step 5: Modify `src/octopus_mcp/server.py`** to wire Kraken and register new tools

In `_build_app` after creating `ctx`, add:

```python
        from octopus_mcp.cache.kraken_repo import KrakenRepo
        from octopus_mcp.octopus.kraken import KrakenClient

        ctx.kraken_repo = KrakenRepo(conn)
        ctx.kraken = KrakenClient(creds)
```

(Move the `build_helpers(ctx)` call to after this so `ensure_kraken_synced` can reference `ctx.kraken`.)

Register the two new tools alongside the others:

```python
    from octopus_mcp.tools.kraken_passthrough import kraken_query as _kraken_query_tool
    from octopus_mcp.tools.saving_sessions import saving_session_history

    @app.tool(name="saving_session_history", description="Octoplus saving sessions joined and points/kWh earned")
    async def _saving_sessions() -> dict[str, Any]:
        return await _wrap(lambda ctx: saving_session_history(ctx=ctx))()

    @app.tool(name="kraken_query", description="Escape hatch: run an arbitrary Kraken GraphQL query")
    async def _kraken_query(query: str, variables: dict | None = None) -> dict[str, Any]:
        return await _wrap(lambda ctx: _kraken_query_tool(query, variables, ctx=ctx))()
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/tools/test_saving_sessions.py tests/test_server.py -v
```

Expected: PASS. Update server smoke test (Task 25) to include `saving_session_history` and `kraken_query` in the expected name set.

- [ ] **Step 7: Commit**

```bash
git add src/octopus_mcp/tools/saving_sessions.py src/octopus_mcp/tools/kraken_passthrough.py src/octopus_mcp/tools/context.py src/octopus_mcp/server.py tests/tools/test_saving_sessions.py tests/test_server.py
git commit -m "feat(tools): saving_session_history and kraken_query, wired into server"
```

---

## Phase 7 — Plugin & release

### Task 29: Claude Code plugin (manifest, .mcp.json, commands, skill)

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.mcp.json`
- Create: `commands/bill.md`
- Create: `commands/compare.md`
- Create: `commands/peaks.md`
- Create: `commands/saving-sessions.md`
- Create: `skills/octopus-analysis/SKILL.md`

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "octopus",
  "version": "0.1.0",
  "description": "Analyse your Octopus Energy account with Claude.",
  "author": "Daniel Chicot",
  "homepage": "https://github.com/DanielChicot/octopus-mcp"
}
```

- [ ] **Step 2: Create `.mcp.json`**

```json
{
  "mcpServers": {
    "octopus": {
      "command": "uvx",
      "args": ["octopus-mcp"]
    }
  }
}
```

- [ ] **Step 3: Create `commands/bill.md`**

```markdown
---
description: Show your Octopus bill summary for a period (default last_month).
argument-hint: "[period]"
---

Use the `bill_summary` MCP tool with `period.kind = "$1"` (default `last_month` if `$1` is empty).

Format the result as a markdown table:
- Columns: Fuel | kWh | Unit £ | Standing £ | Total £
- Add a final row with the grand total.
- Mention any caveats from the response in a short footnote.
- If `fuels_unavailable` is non-empty, note which fuels were skipped and why.
```

- [ ] **Step 4: Create `commands/compare.md`**

```markdown
---
description: Compare your current tariff against another Octopus product.
argument-hint: "<product-code> [period]"
---

Use the `compare_tariff` MCP tool with:
- `target_product_code = "$1"`
- `period.kind = "$2"` (default `last_month`)
- `fuel = "both"`

Format:
- Top line: the `pounds_summary` field, prominent.
- Per-fuel table: Fuel | Current £ | Target £ | Delta £.
- Show the per-day breakdown as a small markdown table beneath, sorted by date.
- List every entry in `caveats[]` as bullets at the end. Do NOT hide them.
- If the tool returns an error mentioning Intelligent Octopus, suggest trying `GO-VAR-22-10-14` or `COSY-22-12-08` instead.
```

- [ ] **Step 5: Create `commands/peaks.md`**

```markdown
---
description: Show your top-N highest-usage half-hours.
argument-hint: "[period] [top_n]"
---

Use the `peak_hours` MCP tool with:
- `period.kind = "$1"` (default `last_7_days`)
- `top_n = $2` (default `10`, must be an integer)

Format per fuel: a numbered list of half-hours with kWh, ordered descending. Convert UTC to Europe/London for display.
```

- [ ] **Step 6: Create `commands/saving-sessions.md`**

```markdown
---
description: Octoplus saving session history and rewards earned.
---

Use the `saving_session_history` MCP tool.

Format:
- A summary line with totals (sessions joined, points awarded, kWh saved).
- A markdown table of sessions: Date | Code | Joined | Points | kWh Saved.
- A short list of recent Octoplus events.
- If `sessions_joined == 0` but there are sessions, suggest joining future ones.
```

- [ ] **Step 7: Create `skills/octopus-analysis/SKILL.md`**

```markdown
---
name: octopus-analysis
description: Use when the user asks about their Octopus Energy bill, usage, tariff, or saving sessions — questions like "how much did I spend", "when do I use most electricity", "should I switch tariff", "how am I doing on saving sessions". Provides a playbook for combining the Octopus MCP tools.
---

# Octopus account analysis

When the user asks about their Octopus Energy account, use the MCP tools — never invent figures.

## Quick playbook

| User asks | Tool to call first |
|---|---|
| "How much did I spend last month?" | `bill_summary` with `period.kind = "last_month"` |
| "What did I use last week?" | `usage_breakdown` with `period.kind = "last_7_days"`, `group_by = "day"` |
| "When am I using the most electricity?" | `peak_hours` with `period.kind = "last_30_days"` (use `last_quarter` if 30 days isn't a kind), `top_n = 10` |
| "Should I switch to Tracker / Agile / Cosy / Go?" | `compare_tariff` with the relevant `target_product_code` |
| "How am I doing on saving sessions?" | `saving_session_history` |
| "What tariff am I on?" | `current_tariff` |

## Conventions

- Always state the period analysed and the units (pence inc-VAT, kWh) so the user can sanity-check.
- When a tool returns `caveats`, show them — they prevent the user being misled by simplified projections.
- For tariff comparisons, lead with the `pounds_summary` headline and put the detail underneath.
- For peak analysis, convert UTC timestamps to Europe/London (BST when applicable) before presenting.
- If the user mentions a tariff name without a code (e.g. "Tracker"), call `list_products` and pick a sensible matching `code`. If multiple match, ask the user which.
- Never speculate about Saving Sessions earnings — only report what `saving_session_history` returns.

## Things not to do

- Don't claim the user "would have saved" anything beyond the `delta_pence` returned — the model is a pure tariff swap, not a behavioural projection.
- Don't recommend Intelligent Octopus; the comparator can't model dispatches and the tool returns an error guiding to alternatives.
- Don't write to the user's Octopus account; the MCP is read-only.
```

- [ ] **Step 8: Verify the plugin loads in Claude Code (manual)**

```bash
# In Claude Code, from this repo:
/plugin reload  # or restart Claude Code
/octopus:bill last_month
```

Expected: command runs `bill_summary` against your account. (Requires `octopus-mcp configure` to have been run.)

- [ ] **Step 9: Commit**

```bash
git add .claude-plugin/ .mcp.json commands/ skills/
git commit -m "feat(plugin): Claude Code plugin manifest, slash commands, and analysis skill"
```

---

### Task 30: Release pipeline + README polish

**Files:**
- Create: `.github/workflows/release.yml`
- Modify: `README.md` (full version)

- [ ] **Step 1: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags: ["v*.*.*"]

permissions:
  contents: write
  id-token: write  # for PyPI trusted publishing

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3

      - name: Set up Python
        run: uv python install 3.12

      - name: Verify version matches tag
        run: |
          PKG_VERSION=$(uv run python -c "import octopus_mcp; print(octopus_mcp.__version__)")
          TAG_VERSION="${GITHUB_REF_NAME#v}"
          if [ "$PKG_VERSION" != "$TAG_VERSION" ]; then
            echo "Tag $TAG_VERSION does not match package version $PKG_VERSION"
            exit 1
          fi

      - name: Sync plugin manifest version
        run: |
          TAG_VERSION="${GITHUB_REF_NAME#v}"
          python -c "
          import json, pathlib
          p = pathlib.Path('.claude-plugin/plugin.json')
          d = json.loads(p.read_text())
          d['version'] = '$TAG_VERSION'
          p.write_text(json.dumps(d, indent=2) + '\n')
          "

      - name: Build distribution
        run: uv build

      - name: Publish to PyPI (trusted publishing)
        uses: pypa/gh-action-pypi-publish@release/v1

      - name: Bundle plugin assets
        run: |
          tar -czf octopus-plugin-${GITHUB_REF_NAME}.tar.gz \
            .claude-plugin .mcp.json commands skills

      - name: Create GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/*
            octopus-plugin-*.tar.gz
          generate_release_notes: true
```

- [ ] **Step 2: Replace `README.md` with the full version**

```markdown
# octopus-mcp

> Unofficial. Not affiliated with Octopus Energy. Uses the public REST API and the community-known Kraken GraphQL endpoint; the latter is unofficial and may break without notice.

A Model Context Protocol server that lets Claude analyse your Octopus Energy account: usage, costs, tariff comparisons, Saving Sessions, Octoplus rewards.

Works with **Claude Code**, **Claude Desktop**, and any MCP-compatible client.

## Install

### Claude Code (recommended)

```bash
# 1. Install the MCP server
uv tool install octopus-mcp

# 2. Save your credentials in your OS keychain
octopus-mcp configure

# 3. Install the plugin from this repo
# In Claude Code:
/plugin install DanielChicot/octopus-mcp
```

### Claude Desktop / Cursor / other MCP clients

Install the server, configure credentials, then add to your MCP client config:

```json
{
  "mcpServers": {
    "octopus": {
      "command": "uvx",
      "args": ["octopus-mcp"]
    }
  }
}
```

For Claude Desktop, the config lives at `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

## Credentials

You need:

- `OCTOPUS_API_KEY` — find at [octopus.energy → My account → Personal details → Developer settings](https://octopus.energy/dashboard/new/accounts/personal-details/api-access)
- `OCTOPUS_ACCOUNT_NUMBER` — `A-XXXXXXXX`, on any bill or in your account

Optional (only some Kraken queries):

- `OCTOPUS_EMAIL` / `OCTOPUS_PASSWORD`

Resolution order: shell env > `.env` > OS keyring > error. The recommended path is `octopus-mcp configure` which writes to the OS keyring so secrets never sit in plaintext config.

## Tools

| Tool | What it does |
|---|---|
| `bill_summary(period)` | Total kWh and £ per fuel for a period |
| `usage_breakdown(period, group_by)` | Aggregated kWh by hour/day/week/month |
| `peak_hours(period, top_n)` | Top-N highest-usage half-hours |
| `compare_tariff(target_product_code, period, fuel)` | Replay your usage against another Octopus tariff |
| `current_tariff()` | What you're on now: unit rate, standing charge |
| `saving_session_history()` | Octoplus saving sessions joined and rewards earned |
| `get_account()`, `list_products()`, `get_product()`, `get_consumption_raw()`, `kraken_query()` | Thin getters / escape hatches |

## Slash commands (Claude Code plugin)

- `/octopus:bill [period]` — bill summary as a markdown table
- `/octopus:compare <product-code> [period]` — tariff comparison with caveats
- `/octopus:peaks [period] [top_n]` — highest-usage half-hours
- `/octopus:saving-sessions` — Octoplus history

## How it works

- A SQLite cache at `~/Library/Caches/octopus-mcp/` (or your platform's equivalent) holds your historical consumption and tariff data, refreshed incrementally.
- All cost figures are in integer pence inc-VAT (no float drift), with a derived pounds string for display.
- Tariff comparison is a *pure tariff swap* model — caveats list what it does and doesn't model. See the design doc.

## Privacy

The MCP runs on your machine. No data leaves your computer except direct calls to `api.octopus.energy`. Credentials live in your OS keychain. Logs at `~/Library/Logs/octopus-mcp/server.log` redact secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `pre-commit run --all-files` before pushing.

## License

MIT — see [LICENSE](LICENSE).
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml README.md
git commit -m "chore(release): release pipeline and full README"
```

- [ ] **Step 4: Tag the first release (manual, when ready)**

```bash
git tag v0.1.0
git push origin v0.1.0
```

This will trigger `release.yml` to build, publish to PyPI, sync the plugin version, and cut a GitHub release with the plugin tarball attached.

---

## Self-review checklist

After implementing the plan, verify:

- [ ] All 30 tasks committed in order; `git log --oneline` reads as a clean story
- [ ] `pytest` passes with coverage ≥ 75% overall, ≥ 90% on `analysis/`
- [ ] `ruff check . && ruff format --check . && mypy` all pass
- [ ] `pre-commit run --all-files` passes (including gitleaks)
- [ ] `octopus-mcp configure` walks through interactively without crashing on cancel
- [ ] `octopus-mcp serve` boots and the e2e smoke test passes
- [ ] All 9 MVP tools (Phases 0–5) return well-shaped data when wired to a real account
- [ ] Phase 6 Kraken tools either work, or fail clean with `DataError` if the schema has drifted
- [ ] Plugin manifest, `.mcp.json`, commands, and skill load in Claude Code without warnings
- [ ] Spec at `docs/superpowers/specs/2026-04-26-octopus-mcp-design.md` has zero uncovered features
- [ ] README install instructions actually work end-to-end on a fresh machine

## Known limitations (deferred to v0.2)

These are spec-acknowledged simplifications consciously made to keep v0.1 tight. They should be documented in the README under a "Known limitations" heading:

1. **Gas unit normalisation.** For SMETS2 meters that report in m³ rather than kWh, v0.1 stores the raw value. Workaround: multiply gas figures by ~11.18 to get kWh. v0.2 will detect the unit and apply the calorific-value conversion described in the spec.
2. **Region-aware tariff resolution.** `compare_tariff` picks the first region's tariff variant from a target product. For most users this is fine since a product's regional rates are similar in shape, but the absolute pence figures can be off. v0.2 will use the user's actual region (derived from the account postcode + product `regions` map).
3. **TTL configuration.** TTLs (24h for products/rates, 7d for meters, 30min for consumption) are hardcoded constants. The spec mentions `config.toml` overrides; v0.2 will load them from there.
4. **`--no-cache` flag.** Spec mentions a server-level bypass flag. v0.1 ships only the `octopus-mcp resync` CLI as the cache reset mechanism. Add the flag in v0.2.
5. **Background sync.** Explicitly out of v1 scope; revisit when ready ("schedules later").


