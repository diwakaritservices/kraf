# Project Initializer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `pipx`-installable interactive Python CLI that scaffolds production-ready Django, Django REST Framework, and FastAPI projects from composable template packs.

**Architecture:** The CLI collects answers, normalizes them into a `ProjectConfig`, resolves compatible packs, renders Jinja templates, merges dependencies and Makefile targets, and writes a generated project. The package keeps prompts, config normalization, pack loading, pack resolution, rendering, and built-in templates in separate modules so each unit is testable.

**Tech Stack:** Python 3.11+, Typer, Jinja2, PyYAML, pytest, Ruff.

---

## File Structure

Create this package structure:

```text
pyproject.toml
README.md
src/project_initializer/
  __init__.py
  cli.py
  config.py
  errors.py
  name_utils.py
  pack.py
  prompts.py
  renderer.py
  resources.py
  packs/
    common/
    django/
    django_drf/
    fastapi/
    database_sqlite/
    database_postgres/
    orm_sqlalchemy/
    migrations_alembic/
    tooling_pytest/
    tooling_ruff/
    docker/
tests/
  test_name_utils.py
  test_config.py
  test_pack_loading.py
  test_resolver.py
  test_renderer.py
  test_cli.py
```

Responsibilities:

- `cli.py`: Typer app entrypoint and command wiring.
- `prompts.py`: Interactive prompt functions that return raw answers.
- `config.py`: Dataclasses/enums and raw-answer normalization.
- `name_utils.py`: Project-name and package-name normalization.
- `pack.py`: Pack manifest model, loading, validation, and dependency resolution.
- `renderer.py`: Jinja rendering, dependency merging, Makefile generation, and filesystem writes.
- `resources.py`: Locate built-in packs from package resources.
- `errors.py`: Project-specific exception types with user-facing messages.
- `src/project_initializer/packs/*`: Built-in pack manifests and templates.
- `tests/*`: Focused tests for normalization, resolver behavior, rendering, and CLI integration.

---

### Task 1: Package Skeleton and CLI Entrypoint

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/project_initializer/__init__.py`
- Create: `src/project_initializer/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from project_initializer.cli import app


def test_version_command_displays_package_version():
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "pypro 0.1.0" in result.stdout
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_cli.py::test_version_command_displays_package_version -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'project_initializer'`.

- [ ] **Step 3: Create package metadata and entrypoint**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "django-project-initializer"
version = "0.1.0"
description = "Interactive Python web project initializer for Django, Django REST Framework, and FastAPI."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "jinja2>=3.1.0",
  "pyyaml>=6.0.0",
  "typer>=0.12.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "ruff>=0.5.0",
]

[project.scripts]
pypro = "project_initializer.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.hatch.build.targets.wheel]
packages = ["src/project_initializer"]

[tool.hatch.build.targets.sdist]
include = [
  "/README.md",
  "/pyproject.toml",
  "/src",
  "/tests",
]
```

Create `README.md`:

````markdown
# Django Project Initializer

Interactive Python web project initializer for Django, Django REST Framework, and FastAPI.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```
````

Create `src/project_initializer/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/project_initializer/cli.py`:

```python
from typing import Annotated

import typer

from project_initializer import __version__

app = typer.Typer(
    name="pypro",
    help="Create production-ready Python web projects from interactive prompts.",
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pypro {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed pypro version.", callback=_version_callback),
    ] = False,
) -> None:
    return None


@app.command()
def new() -> None:
    typer.echo("Project generation is not wired yet.")
```

- [ ] **Step 4: Run the CLI smoke test**

Run:

```bash
pytest tests/test_cli.py::test_version_command_displays_package_version -v
```

Expected: PASS.

- [ ] **Step 5: Run lint for new files**

Run:

```bash
ruff check src tests
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md src/project_initializer/__init__.py src/project_initializer/cli.py tests/test_cli.py
git commit -m "feat: add package skeleton"
```

---

### Task 2: Name Normalization and Project Config

**Files:**
- Create: `src/project_initializer/errors.py`
- Create: `src/project_initializer/name_utils.py`
- Create: `src/project_initializer/config.py`
- Create: `tests/test_name_utils.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for name normalization**

Create `tests/test_name_utils.py`:

```python
import pytest

from project_initializer.errors import InvalidProjectNameError
from project_initializer.name_utils import normalize_package_name, normalize_project_slug


def test_normalize_project_slug():
    assert normalize_project_slug("Customer API") == "customer-api"


def test_normalize_package_name():
    assert normalize_package_name("Customer API") == "customer_api"


def test_package_name_cannot_start_with_digit():
    with pytest.raises(InvalidProjectNameError, match="valid Python package"):
        normalize_package_name("123 API")


def test_package_name_rejects_empty_input():
    with pytest.raises(InvalidProjectNameError, match="Project name is required"):
        normalize_package_name("   ")
```

- [ ] **Step 2: Write failing tests for config normalization**

Create `tests/test_config.py`:

```python
from project_initializer.config import Database, ProjectType, ToolingOptions, normalize_answers


def test_normalize_django_drf_answers_selects_django_stack():
    config = normalize_answers(
        {
            "project_name": "Customer API",
            "project_type": "django_drf",
            "database": "postgresql",
            "use_docker": True,
            "use_pytest": True,
            "use_ruff": True,
            "use_sqlalchemy": False,
            "use_alembic": False,
        }
    )

    assert config.project_name == "Customer API"
    assert config.project_slug == "customer-api"
    assert config.package_name == "customer_api"
    assert config.project_type is ProjectType.DJANGO_DRF
    assert config.database is Database.POSTGRESQL
    assert config.tooling == ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True)


def test_fastapi_without_sqlalchemy_disables_alembic():
    config = normalize_answers(
        {
            "project_name": "Inventory Service",
            "project_type": "fastapi",
            "database": "sqlite",
            "use_docker": False,
            "use_pytest": True,
            "use_ruff": True,
            "use_sqlalchemy": False,
            "use_alembic": True,
        }
    )

    assert config.use_sqlalchemy is False
    assert config.use_alembic is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest tests/test_name_utils.py tests/test_config.py -v
```

Expected: FAIL because the modules are not implemented.

- [ ] **Step 4: Implement project errors**

Create `src/project_initializer/errors.py`:

```python
class ProjectInitializerError(Exception):
    """Base class for user-facing project initializer errors."""


class InvalidProjectNameError(ProjectInitializerError):
    """Raised when a project name cannot produce a valid slug or package name."""


class PackError(ProjectInitializerError):
    """Raised when pack manifests or pack selections are invalid."""


class RenderError(ProjectInitializerError):
    """Raised when a project cannot be rendered safely."""
```

- [ ] **Step 5: Implement name normalization**

Create `src/project_initializer/name_utils.py`:

```python
import keyword
import re

from project_initializer.errors import InvalidProjectNameError


_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_MULTIPLE_DASHES = re.compile(r"-+")
_MULTIPLE_UNDERSCORES = re.compile(r"_+")


def normalize_project_slug(project_name: str) -> str:
    cleaned = project_name.strip()
    if not cleaned:
        raise InvalidProjectNameError("Project name is required.")

    slug = _NON_ALNUM.sub("-", cleaned).strip("-").lower()
    slug = _MULTIPLE_DASHES.sub("-", slug)
    if not slug:
        raise InvalidProjectNameError("Project name must contain letters or numbers.")
    return slug


def normalize_package_name(project_name: str) -> str:
    cleaned = project_name.strip()
    if not cleaned:
        raise InvalidProjectNameError("Project name is required.")

    package_name = _NON_ALNUM.sub("_", cleaned).strip("_").lower()
    package_name = _MULTIPLE_UNDERSCORES.sub("_", package_name)

    if not package_name or not package_name.isidentifier() or keyword.iskeyword(package_name):
        raise InvalidProjectNameError(
            f"Project name '{project_name}' cannot be converted into a valid Python package name."
        )

    return package_name
```

- [ ] **Step 6: Implement config models and normalization**

Create `src/project_initializer/config.py`:

```python
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from project_initializer.name_utils import normalize_package_name, normalize_project_slug


class ProjectType(StrEnum):
    DJANGO = "django"
    DJANGO_DRF = "django_drf"
    FASTAPI = "fastapi"


class Database(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass(frozen=True)
class ToolingOptions:
    use_docker: bool
    use_pytest: bool
    use_ruff: bool


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    project_slug: str
    package_name: str
    target_dir: Path
    project_type: ProjectType
    database: Database
    tooling: ToolingOptions
    use_sqlalchemy: bool
    use_alembic: bool


def normalize_answers(raw_answers: dict[str, Any], base_dir: Path | None = None) -> ProjectConfig:
    project_name = str(raw_answers["project_name"]).strip()
    project_type = ProjectType(str(raw_answers["project_type"]))
    database = Database(str(raw_answers["database"]))
    package_name = normalize_package_name(project_name)
    project_slug = normalize_project_slug(project_name)
    target_root = base_dir or Path.cwd()

    use_sqlalchemy = bool(raw_answers.get("use_sqlalchemy", False))
    use_alembic = bool(raw_answers.get("use_alembic", False))
    if project_type is not ProjectType.FASTAPI:
        use_sqlalchemy = False
        use_alembic = False
    if not use_sqlalchemy:
        use_alembic = False

    return ProjectConfig(
        project_name=project_name,
        project_slug=project_slug,
        package_name=package_name,
        target_dir=target_root / project_slug,
        project_type=project_type,
        database=database,
        tooling=ToolingOptions(
            use_docker=bool(raw_answers.get("use_docker", False)),
            use_pytest=bool(raw_answers.get("use_pytest", True)),
            use_ruff=bool(raw_answers.get("use_ruff", True)),
        ),
        use_sqlalchemy=use_sqlalchemy,
        use_alembic=use_alembic,
    )
```

- [ ] **Step 7: Run the focused tests**

Run:

```bash
pytest tests/test_name_utils.py tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/project_initializer/errors.py src/project_initializer/name_utils.py src/project_initializer/config.py tests/test_name_utils.py tests/test_config.py
git commit -m "feat: add project configuration model"
```

---

### Task 3: Pack Manifest Loading and Resolution

**Files:**
- Create: `src/project_initializer/pack.py`
- Create: `tests/test_pack_loading.py`
- Create: `tests/test_resolver.py`

- [ ] **Step 1: Write failing pack loading tests**

Create `tests/test_pack_loading.py`:

```python
from pathlib import Path

import pytest

from project_initializer.errors import PackError
from project_initializer.pack import PackManifest, load_pack


def test_load_pack_manifest(tmp_path: Path):
    pack_dir = tmp_path / "fastapi"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        """
name: fastapi
dependencies:
  - fastapi
dev_dependencies:
  - pytest
files:
  - source: app/main.py.j2
    destination: app/main.py
make_targets:
  run: "uvicorn app.main:app --reload"
requires: []
conflicts:
  - django
""".strip(),
        encoding="utf-8",
    )

    manifest = load_pack(pack_dir)

    assert manifest == PackManifest(
        name="fastapi",
        dependencies=("fastapi",),
        dev_dependencies=("pytest",),
        files=(("app/main.py.j2", "app/main.py"),),
        make_targets={"run": "uvicorn app.main:app --reload"},
        env={},
        requires=(),
        conflicts=("django",),
    )


def test_load_pack_requires_name(tmp_path: Path):
    pack_dir = tmp_path / "broken"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text("dependencies: []", encoding="utf-8")

    with pytest.raises(PackError, match="missing required field 'name'"):
        load_pack(pack_dir)
```

- [ ] **Step 2: Write failing resolver tests**

Create `tests/test_resolver.py`:

```python
import pytest
from pathlib import Path

from project_initializer.config import Database, ProjectConfig, ProjectType, ToolingOptions
from project_initializer.errors import PackError
from project_initializer.pack import PackManifest, resolve_packs


def _config(project_type: ProjectType, *, sqlalchemy: bool = False, alembic: bool = False):
    return ProjectConfig(
        project_name="Customer API",
        project_slug="customer-api",
        package_name="customer_api",
        target_dir=Path("customer-api"),
        project_type=project_type,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True),
        use_sqlalchemy=sqlalchemy,
        use_alembic=alembic,
    )


def test_resolve_fastapi_sqlalchemy_alembic_packs():
    packs = resolve_packs(_config(ProjectType.FASTAPI, sqlalchemy=True, alembic=True))

    assert [pack.name for pack in packs] == [
        "common",
        "fastapi",
        "database_postgres",
        "orm_sqlalchemy",
        "migrations_alembic",
        "tooling_pytest",
        "tooling_ruff",
        "docker",
    ]


def test_resolve_django_drf_packs():
    packs = resolve_packs(_config(ProjectType.DJANGO_DRF))

    assert [pack.name for pack in packs] == [
        "common",
        "django",
        "django_drf",
        "database_postgres",
        "tooling_pytest",
        "tooling_ruff",
        "docker",
    ]


def test_validate_pack_conflict():
    with pytest.raises(PackError, match="conflicts with selected pack"):
        resolve_packs(
            _config(ProjectType.DJANGO),
            available_packs={
                "common": PackManifest(name="common"),
                "django": PackManifest(name="django", conflicts=("fastapi",)),
                "fastapi": PackManifest(name="fastapi", conflicts=("django",)),
            },
            explicit_names=["common", "django", "fastapi"],
        )
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest tests/test_pack_loading.py tests/test_resolver.py -v
```

Expected: FAIL because `pack.py` is not implemented.

- [ ] **Step 4: Implement pack loading and resolution**

Create `src/project_initializer/pack.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from project_initializer.config import Database, ProjectConfig, ProjectType
from project_initializer.errors import PackError


@dataclass(frozen=True)
class PackManifest:
    name: str
    dependencies: tuple[str, ...] = ()
    dev_dependencies: tuple[str, ...] = ()
    files: tuple[tuple[str, str], ...] = ()
    make_targets: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


def load_pack(pack_dir: Path) -> PackManifest:
    manifest_path = pack_dir / "pack.yaml"
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise PackError(f"Pack at {pack_dir} is missing pack.yaml.") from exc
    except yaml.YAMLError as exc:
        raise PackError(f"Pack at {pack_dir} has invalid YAML: {exc}") from exc

    if "name" not in raw:
        raise PackError(f"Pack at {pack_dir} is missing required field 'name'.")

    return _manifest_from_mapping(raw, pack_dir)


def _manifest_from_mapping(raw: dict[str, Any], pack_dir: Path) -> PackManifest:
    files = []
    for file_entry in raw.get("files", []):
        source = file_entry.get("source")
        destination = file_entry.get("destination")
        if not source or not destination:
            raise PackError(f"Pack at {pack_dir} has a file entry without source and destination.")
        files.append((str(source), str(destination)))

    return PackManifest(
        name=str(raw["name"]),
        dependencies=tuple(str(item) for item in raw.get("dependencies", [])),
        dev_dependencies=tuple(str(item) for item in raw.get("dev_dependencies", [])),
        files=tuple(files),
        make_targets={str(key): str(value) for key, value in raw.get("make_targets", {}).items()},
        env={str(key): str(value) for key, value in raw.get("env", {}).items()},
        requires=tuple(str(item) for item in raw.get("requires", [])),
        conflicts=tuple(str(item) for item in raw.get("conflicts", [])),
    )


def resolve_packs(
    config: ProjectConfig,
    *,
    available_packs: dict[str, PackManifest] | None = None,
    explicit_names: list[str] | None = None,
) -> list[PackManifest]:
    pack_map = available_packs or _default_pack_manifest_map()
    names = explicit_names or _pack_names_for_config(config)

    selected = [_require_pack(pack_map, name) for name in names]
    selected_names = {pack.name for pack in selected}

    for pack in selected:
        for required in pack.requires:
            if required not in selected_names:
                raise PackError(f"Pack '{pack.name}' requires pack '{required}'.")
        for conflict in pack.conflicts:
            if conflict in selected_names:
                raise PackError(f"Pack '{pack.name}' conflicts with selected pack '{conflict}'.")

    return selected


def _require_pack(pack_map: dict[str, PackManifest], name: str) -> PackManifest:
    try:
        return pack_map[name]
    except KeyError as exc:
        raise PackError(f"Required pack '{name}' is not available.") from exc


def _pack_names_for_config(config: ProjectConfig) -> list[str]:
    names = ["common"]

    if config.project_type is ProjectType.DJANGO:
        names.append("django")
    elif config.project_type is ProjectType.DJANGO_DRF:
        names.extend(["django", "django_drf"])
    elif config.project_type is ProjectType.FASTAPI:
        names.append("fastapi")

    if config.database is Database.SQLITE:
        names.append("database_sqlite")
    elif config.database is Database.POSTGRESQL:
        names.append("database_postgres")

    if config.use_sqlalchemy:
        names.append("orm_sqlalchemy")
    if config.use_alembic:
        names.append("migrations_alembic")
    if config.tooling.use_pytest:
        names.append("tooling_pytest")
    if config.tooling.use_ruff:
        names.append("tooling_ruff")
    if config.tooling.use_docker:
        names.append("docker")

    return names


def _default_pack_manifest_map() -> dict[str, PackManifest]:
    return {
        "common": PackManifest(name="common"),
        "django": PackManifest(name="django", conflicts=("fastapi",)),
        "django_drf": PackManifest(name="django_drf", requires=("django",), conflicts=("fastapi",)),
        "fastapi": PackManifest(name="fastapi", conflicts=("django", "django_drf")),
        "database_sqlite": PackManifest(name="database_sqlite"),
        "database_postgres": PackManifest(name="database_postgres"),
        "orm_sqlalchemy": PackManifest(name="orm_sqlalchemy", requires=("fastapi",)),
        "migrations_alembic": PackManifest(
            name="migrations_alembic", requires=("orm_sqlalchemy",)
        ),
        "tooling_pytest": PackManifest(name="tooling_pytest"),
        "tooling_ruff": PackManifest(name="tooling_ruff"),
        "docker": PackManifest(name="docker"),
    }
```

- [ ] **Step 5: Run the focused tests**

Run:

```bash
pytest tests/test_pack_loading.py tests/test_resolver.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/project_initializer/pack.py tests/test_pack_loading.py tests/test_resolver.py
git commit -m "feat: add pack resolution"
```

---

### Task 4: Renderer and Filesystem Safety

**Files:**
- Create: `src/project_initializer/renderer.py`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_renderer.py`:

```python
from pathlib import Path

import pytest

from project_initializer.config import Database, ProjectConfig, ProjectType, ToolingOptions
from project_initializer.errors import RenderError
from project_initializer.pack import PackManifest
from project_initializer.renderer import RenderedProject, render_project


def _config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig(
        project_name="Customer API",
        project_slug="customer-api",
        package_name="customer_api",
        target_dir=tmp_path / "customer-api",
        project_type=ProjectType.FASTAPI,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        use_sqlalchemy=False,
        use_alembic=False,
    )


def test_render_project_writes_templates_and_merged_files(tmp_path: Path):
    pack_root = tmp_path / "packs"
    pack_dir = pack_root / "fastapi"
    template_dir = pack_dir / "templates" / "app"
    template_dir.mkdir(parents=True)
    (template_dir / "main.py.j2").write_text(
        'APP_NAME = "{{ project.project_name }}"\\n',
        encoding="utf-8",
    )
    pack = PackManifest(
        name="fastapi",
        dependencies=("fastapi",),
        dev_dependencies=("pytest",),
        files=(("app/main.py.j2", "app/main.py"),),
        make_targets={"run": "uvicorn app.main:app --reload"},
        env={"APP_ENV": "local"},
    )

    result = render_project(_config(tmp_path), [(pack, pack_dir)])

    assert result == RenderedProject(path=tmp_path / "customer-api", files_written=5)
    assert (tmp_path / "customer-api" / "app" / "main.py").read_text(encoding="utf-8") == (
        'APP_NAME = "Customer API"\\n'
    )
    assert "fastapi" in (tmp_path / "customer-api" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert "pytest" in (tmp_path / "customer-api" / "requirements-dev.txt").read_text(
        encoding="utf-8"
    )
    assert "run:" in (tmp_path / "customer-api" / "Makefile").read_text(encoding="utf-8")
    assert "APP_ENV=local" in (tmp_path / "customer-api" / ".env.example").read_text(
        encoding="utf-8"
    )


def test_render_project_rejects_non_empty_target(tmp_path: Path):
    config = _config(tmp_path)
    config.target_dir.mkdir()
    (config.target_dir / "existing.txt").write_text("data", encoding="utf-8")

    with pytest.raises(RenderError, match="already exists and is not empty"):
        render_project(config, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_renderer.py -v
```

Expected: FAIL because `renderer.py` is not implemented.

- [ ] **Step 3: Implement renderer**

Create `src/project_initializer/renderer.py`:

```python
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from project_initializer.config import ProjectConfig
from project_initializer.errors import RenderError
from project_initializer.pack import PackManifest


@dataclass(frozen=True)
class RenderedProject:
    path: Path
    files_written: int


PackWithPath = tuple[PackManifest, Path]


def render_project(config: ProjectConfig, packs: list[PackWithPath]) -> RenderedProject:
    _ensure_target_is_safe(config.target_dir)
    config.target_dir.mkdir(parents=True, exist_ok=True)

    files_written = 0
    for pack, pack_dir in packs:
        files_written += _render_pack_files(config, pack, pack_dir)

    files_written += _write_requirements(config.target_dir, packs)
    files_written += _write_makefile(config.target_dir, packs)
    files_written += _write_env_example(config.target_dir, packs)

    return RenderedProject(path=config.target_dir, files_written=files_written)


def _ensure_target_is_safe(target_dir: Path) -> None:
    if target_dir.exists() and any(target_dir.iterdir()):
        raise RenderError(f"Target directory '{target_dir}' already exists and is not empty.")


def _render_pack_files(config: ProjectConfig, pack: PackManifest, pack_dir: Path) -> int:
    template_root = pack_dir / "templates"
    environment = Environment(
        loader=FileSystemLoader(template_root),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    files_written = 0
    for source, destination in pack.files:
        try:
            rendered = environment.get_template(source).render(project=config)
            rendered_destination = environment.from_string(destination).render(project=config)
        except TemplateError as exc:
            raise RenderError(f"Failed to render template '{source}' from pack '{pack.name}'.") from exc

        destination_path = _safe_destination_path(config.target_dir, rendered_destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(rendered, encoding="utf-8")
        files_written += 1

    return files_written


def _safe_destination_path(target_dir: Path, destination: str) -> Path:
    destination_path = Path(destination)
    if destination_path.is_absolute() or ".." in destination_path.parts:
        raise RenderError(f"Refusing to write unsafe template destination '{destination}'.")
    return target_dir / destination_path


def _write_requirements(target_dir: Path, packs: list[PackWithPath]) -> int:
    dependencies = _unique_sorted(item for pack, _path in packs for item in pack.dependencies)
    dev_dependencies = _unique_sorted(item for pack, _path in packs for item in pack.dev_dependencies)

    (target_dir / "requirements.txt").write_text(_lines(dependencies), encoding="utf-8")
    (target_dir / "requirements-dev.txt").write_text(_lines(dev_dependencies), encoding="utf-8")
    return 2


def _write_makefile(target_dir: Path, packs: list[PackWithPath]) -> int:
    targets: dict[str, str] = {
        "venv": "python -m venv .venv",
        "install": ". .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt",
    }
    for pack, _path in packs:
        targets.update(pack.make_targets)

    content = "\\n".join(f"{name}:\\n\\t{command}\\n" for name, command in targets.items())
    (target_dir / "Makefile").write_text(content, encoding="utf-8")
    return 1


def _write_env_example(target_dir: Path, packs: list[PackWithPath]) -> int:
    env_values: dict[str, str] = {}
    for pack, _path in packs:
        env_values.update(pack.env)

    (target_dir / ".env.example").write_text(
        _lines(f"{key}={value}" for key, value in sorted(env_values.items())),
        encoding="utf-8",
    )
    return 1


def _unique_sorted(values) -> list[str]:
    return sorted({str(value) for value in values if str(value).strip()})


def _lines(values) -> str:
    lines = list(values)
    if not lines:
        return ""
    return "\\n".join(lines) + "\\n"
```

- [ ] **Step 4: Run renderer tests**

Run:

```bash
pytest tests/test_renderer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/project_initializer/renderer.py tests/test_renderer.py
git commit -m "feat: add project renderer"
```

---

### Task 5: Built-In Pack Resources and Manifest Loading

**Files:**
- Create: `src/project_initializer/resources.py`
- Modify: `src/project_initializer/pack.py`
- Create: `src/project_initializer/packs/common/pack.yaml`
- Create: `src/project_initializer/packs/fastapi/pack.yaml`
- Create: `src/project_initializer/packs/django/pack.yaml`
- Create: `src/project_initializer/packs/django_drf/pack.yaml`
- Create: `src/project_initializer/packs/database_sqlite/pack.yaml`
- Create: `src/project_initializer/packs/database_postgres/pack.yaml`
- Create: `src/project_initializer/packs/orm_sqlalchemy/pack.yaml`
- Create: `src/project_initializer/packs/migrations_alembic/pack.yaml`
- Create: `src/project_initializer/packs/tooling_pytest/pack.yaml`
- Create: `src/project_initializer/packs/tooling_ruff/pack.yaml`
- Create: `src/project_initializer/packs/docker/pack.yaml`
- Modify: `tests/test_resolver.py`

- [ ] **Step 1: Add a failing test for real built-in manifests**

Append to `tests/test_resolver.py`:

```python
def test_default_resolver_uses_builtin_pack_manifests():
    packs = resolve_packs(_config(ProjectType.FASTAPI, sqlalchemy=True, alembic=True))

    dependencies = {dependency for pack in packs for dependency in pack.dependencies}

    assert "fastapi" in dependencies
    assert "sqlalchemy" in dependencies
    assert "alembic" in dependencies
```

- [ ] **Step 2: Run the resolver test to verify it fails**

Run:

```bash
pytest tests/test_resolver.py::test_default_resolver_uses_builtin_pack_manifests -v
```

Expected: FAIL because default manifests are currently hard-coded without dependencies.

- [ ] **Step 3: Implement built-in pack resource discovery**

Create `src/project_initializer/resources.py`:

```python
from importlib.resources import files
from pathlib import Path


def builtin_pack_dirs() -> list[Path]:
    pack_root = files("project_initializer") / "packs"
    return sorted(Path(str(item)) for item in pack_root.iterdir() if item.is_dir())
```

- [ ] **Step 4: Replace hard-coded manifests with built-in manifest loading**

In `src/project_initializer/pack.py`, replace `_default_pack_manifest_map` with:

```python
def _default_pack_manifest_map() -> dict[str, PackManifest]:
    from project_initializer.resources import builtin_pack_dirs

    manifests = [load_pack(pack_dir) for pack_dir in builtin_pack_dirs()]
    return {manifest.name: manifest for manifest in manifests}
```

- [ ] **Step 5: Add initial built-in pack manifests**

Create `src/project_initializer/packs/common/pack.yaml`:

```yaml
name: common
files:
  - source: README.md.j2
    destination: README.md
  - source: .gitignore.j2
    destination: .gitignore
make_targets:
  migrate: "python -c \"print('No migrations configured')\""
```

Create `src/project_initializer/packs/fastapi/pack.yaml`:

```yaml
name: fastapi
dependencies:
  - fastapi
  - uvicorn[standard]
files:
  - source: app/main.py.j2
    destination: app/main.py
  - source: app/api/health.py.j2
    destination: app/api/health.py
make_targets:
  run: "uvicorn app.main:app --reload"
conflicts:
  - django
  - django_drf
```

Create `src/project_initializer/packs/django/pack.yaml`:

```yaml
name: django
dependencies:
  - django
files:
  - source: manage.py.j2
    destination: manage.py
  - source: project/settings.py.j2
    destination: "{{ project.package_name }}/settings.py"
  - source: project/urls.py.j2
    destination: "{{ project.package_name }}/urls.py"
  - source: project/wsgi.py.j2
    destination: "{{ project.package_name }}/wsgi.py"
  - source: project/asgi.py.j2
    destination: "{{ project.package_name }}/asgi.py"
make_targets:
  run: "python manage.py runserver"
  migrate: "python manage.py migrate"
  makemigrations: "python manage.py makemigrations"
conflicts:
  - fastapi
```

Create `src/project_initializer/packs/django_drf/pack.yaml`:

```yaml
name: django_drf
dependencies:
  - djangorestframework
files:
  - source: api/views.py.j2
    destination: api/views.py
  - source: api/urls.py.j2
    destination: api/urls.py
requires:
  - django
conflicts:
  - fastapi
```

Create `src/project_initializer/packs/database_sqlite/pack.yaml`:

```yaml
name: database_sqlite
env:
  DATABASE_URL: sqlite:///db.sqlite3
```

Create `src/project_initializer/packs/database_postgres/pack.yaml`:

```yaml
name: database_postgres
dependencies:
  - psycopg[binary]
env:
  DATABASE_URL: postgresql://postgres:postgres@localhost:5432/app
```

Create `src/project_initializer/packs/orm_sqlalchemy/pack.yaml`:

```yaml
name: orm_sqlalchemy
dependencies:
  - sqlalchemy
files:
  - source: app/db/session.py.j2
    destination: app/db/session.py
  - source: app/db/models.py.j2
    destination: app/db/models.py
requires:
  - fastapi
```

Create `src/project_initializer/packs/migrations_alembic/pack.yaml`:

```yaml
name: migrations_alembic
dependencies:
  - alembic
files:
  - source: alembic.ini.j2
    destination: alembic.ini
  - source: alembic/env.py.j2
    destination: alembic/env.py
make_targets:
  migrate: "alembic upgrade head"
  revision: "alembic revision --autogenerate -m \"change\""
requires:
  - orm_sqlalchemy
```

Create `src/project_initializer/packs/tooling_pytest/pack.yaml`:

```yaml
name: tooling_pytest
dev_dependencies:
  - pytest
make_targets:
  test: "pytest"
```

Create `src/project_initializer/packs/tooling_ruff/pack.yaml`:

```yaml
name: tooling_ruff
dev_dependencies:
  - ruff
make_targets:
  lint: "ruff check ."
  format: "ruff format ."
```

Create `src/project_initializer/packs/docker/pack.yaml`:

```yaml
name: docker
files:
  - source: Dockerfile.j2
    destination: Dockerfile
  - source: docker-compose.yml.j2
    destination: docker-compose.yml
make_targets:
  docker-up: "docker compose up --build"
  docker-down: "docker compose down"
```

- [ ] **Step 6: Run resolver tests**

Run:

```bash
pytest tests/test_resolver.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/project_initializer/resources.py src/project_initializer/pack.py src/project_initializer/packs tests/test_resolver.py
git commit -m "feat: load builtin pack manifests"
```

---

### Task 6: Built-In Common, FastAPI, and Tooling Templates

**Files:**
- Create templates under `src/project_initializer/packs/common/templates/`
- Create templates under `src/project_initializer/packs/fastapi/templates/`
- Create templates under `src/project_initializer/packs/orm_sqlalchemy/templates/`
- Create templates under `src/project_initializer/packs/migrations_alembic/templates/`
- Create templates under `src/project_initializer/packs/docker/templates/`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1: Add a failing golden test for FastAPI with SQLAlchemy and Alembic**

Append to `tests/test_renderer.py`:

```python
from project_initializer.pack import resolve_packs
from project_initializer.resources import builtin_pack_dirs


def test_render_builtin_fastapi_sqlalchemy_alembic_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Inventory Service",
        project_slug="inventory-service",
        package_name="inventory_service",
        target_dir=tmp_path / "inventory-service",
        project_type=ProjectType.FASTAPI,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True),
        use_sqlalchemy=True,
        use_alembic=True,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    assert (config.target_dir / "app" / "main.py").exists()
    assert (config.target_dir / "app" / "db" / "session.py").exists()
    assert (config.target_dir / "alembic.ini").exists()
    assert (config.target_dir / "Dockerfile").exists()
    assert "make run" in (config.target_dir / "README.md").read_text(encoding="utf-8")
    assert "alembic upgrade head" in (config.target_dir / "Makefile").read_text(
        encoding="utf-8"
    )
```

- [ ] **Step 2: Run the golden test to verify it fails**

Run:

```bash
pytest tests/test_renderer.py::test_render_builtin_fastapi_sqlalchemy_alembic_project -v
```

Expected: FAIL because templates are not present yet.

- [ ] **Step 3: Add common templates**

Create `src/project_initializer/packs/common/templates/README.md.j2`:

````markdown
# {{ project.project_name }}

Generated with pypro.

## Development

```bash
make venv
make install
make run
```

## Quality

```bash
make test
make lint
make format
```

## Database

```bash
make migrate
```
````

Create `src/project_initializer/packs/common/templates/.gitignore.j2`:

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.env
db.sqlite3
```

- [ ] **Step 4: Add FastAPI templates**

Create `src/project_initializer/packs/fastapi/templates/app/main.py.j2`:

```python
from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="{{ project.project_name }}")
app.include_router(health_router)
```

Create `src/project_initializer/packs/fastapi/templates/app/api/health.py.j2`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Add SQLAlchemy templates**

Create `src/project_initializer/packs/orm_sqlalchemy/templates/app/db/session.py.j2`:

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
```

Create `src/project_initializer/packs/orm_sqlalchemy/templates/app/db/models.py.j2`:

```python
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
```

- [ ] **Step 6: Add Alembic templates**

Create `src/project_initializer/packs/migrations_alembic/templates/alembic.ini.j2`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = %(DATABASE_URL)s

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `src/project_initializer/packs/migrations_alembic/templates/alembic/env.py.j2`:

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
config.set_main_option("sqlalchemy.url", database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Add Docker templates**

Create `src/project_initializer/packs/docker/templates/Dockerfile.j2`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

CMD ["make", "run"]
```

Create `src/project_initializer/packs/docker/templates/docker-compose.yml.j2`:

```yaml
services:
  app:
    build: .
    env_file:
      - .env.example
    ports:
      - "8000:8000"
```

- [ ] **Step 8: Run the FastAPI golden test**

Run:

```bash
pytest tests/test_renderer.py::test_render_builtin_fastapi_sqlalchemy_alembic_project -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/project_initializer/packs tests/test_renderer.py
git commit -m "feat: add fastapi builtin templates"
```

---

### Task 7: Django and Django REST Framework Templates

**Files:**
- Create templates under `src/project_initializer/packs/django/templates/`
- Create templates under `src/project_initializer/packs/django_drf/templates/`
- Modify: `tests/test_renderer.py`

- [ ] **Step 1: Add a failing golden test for Django with DRF and PostgreSQL**

Append to `tests/test_renderer.py`:

```python
def test_render_builtin_django_drf_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Customer API",
        project_slug="customer-api",
        package_name="customer_api",
        target_dir=tmp_path / "customer-api",
        project_type=ProjectType.DJANGO_DRF,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        use_sqlalchemy=False,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    assert (config.target_dir / "manage.py").exists()
    assert (config.target_dir / "customer_api" / "settings.py").exists()
    assert (config.target_dir / "api" / "views.py").exists()
    assert "djangorestframework" in (config.target_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert "python manage.py migrate" in (config.target_dir / "Makefile").read_text(
        encoding="utf-8"
    )
```

- [ ] **Step 2: Run the Django golden test to verify it fails**

Run:

```bash
pytest tests/test_renderer.py::test_render_builtin_django_drf_project -v
```

Expected: FAIL because Django templates are not present yet.

- [ ] **Step 3: Add Django templates**

Create `src/project_initializer/packs/django/templates/manage.py.j2`:

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project.package_name }}.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

Create `src/project_initializer/packs/django/templates/project/settings.py.j2`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
{% if project.project_type.value == "django_drf" %}
    "rest_framework",
    "api",
{% endif %}
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "{{ project.package_name }}.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "{{ project.package_name }}.wsgi.application"

DATABASES = {
    "default": {
{% if project.database.value == "postgresql" %}
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "app"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
{% else %}
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
{% endif %}
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

Create `src/project_initializer/packs/django/templates/project/urls.py.j2`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
{% if project.project_type.value == "django_drf" %}
    path("api/", include("api.urls")),
{% endif %}
]
```

Create `src/project_initializer/packs/django/templates/project/wsgi.py.j2`:

```python
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project.package_name }}.settings")

application = get_wsgi_application()
```

Create `src/project_initializer/packs/django/templates/project/asgi.py.j2`:

```python
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project.package_name }}.settings")

application = get_asgi_application()
```

- [ ] **Step 4: Add Django REST Framework templates**

Create `src/project_initializer/packs/django_drf/templates/api/views.py.j2`:

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})
```

Create `src/project_initializer/packs/django_drf/templates/api/urls.py.j2`:

```python
from django.urls import path

from api.views import health_check

urlpatterns = [
    path("health/", health_check, name="health-check"),
]
```

- [ ] **Step 5: Run the Django golden test**

Run:

```bash
pytest tests/test_renderer.py::test_render_builtin_django_drf_project -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/project_initializer/packs/django src/project_initializer/packs/django_drf tests/test_renderer.py
git commit -m "feat: add django builtin templates"
```

---

### Task 8: Interactive Prompts and CLI Generation

**Files:**
- Create: `src/project_initializer/prompts.py`
- Modify: `src/project_initializer/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI generation test**

Append to `tests/test_cli.py`:

```python
def test_new_command_generates_fastapi_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["new", "--target-root", str(tmp_path)],
        input="Inventory Service\n3\n2\ny\ny\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert "Created project" in result.stdout


def test_root_command_generates_fastapi_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--target-root", str(tmp_path)],
        input="Inventory Service\n3\n2\ny\ny\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert "Created project" in result.stdout
```

- [ ] **Step 2: Run the CLI generation test to verify it fails**

Run:

```bash
pytest tests/test_cli.py::test_new_command_generates_fastapi_project -v
```

Expected: FAIL because prompts and generation are not wired.

- [ ] **Step 3: Implement interactive prompts**

Create `src/project_initializer/prompts.py`:

```python
import typer


def collect_answers() -> dict[str, object]:
    project_name = typer.prompt("Project name")
    project_type = _choice_prompt(
        "Project type",
        {
            "1": "django",
            "2": "django_drf",
            "3": "fastapi",
        },
    )
    database = _choice_prompt(
        "Database",
        {
            "1": "sqlite",
            "2": "postgresql",
        },
    )

    use_sqlalchemy = False
    use_alembic = False
    if project_type == "fastapi":
        use_sqlalchemy = typer.confirm("Use SQLAlchemy ORM?", default=True)
        if use_sqlalchemy:
            use_alembic = typer.confirm("Use Alembic migrations?", default=True)

    return {
        "project_name": project_name,
        "project_type": project_type,
        "database": database,
        "use_sqlalchemy": use_sqlalchemy,
        "use_alembic": use_alembic,
        "use_pytest": typer.confirm("Include pytest?", default=True),
        "use_ruff": typer.confirm("Include Ruff?", default=True),
        "use_docker": typer.confirm("Include Docker?", default=True),
    }


def _choice_prompt(label: str, choices: dict[str, str]) -> str:
    typer.echo(label)
    for key, value in choices.items():
        typer.echo(f"  {key}. {value}")

    while True:
        selected = typer.prompt("Select option")
        if selected in choices:
            return choices[selected]
        typer.echo(f"Choose one of: {', '.join(choices)}")
```

- [ ] **Step 4: Wire CLI generation**

Replace `src/project_initializer/cli.py` with:

```python
from pathlib import Path
from typing import Annotated

import typer

from project_initializer import __version__
from project_initializer.config import normalize_answers
from project_initializer.errors import ProjectInitializerError
from project_initializer.pack import resolve_packs
from project_initializer.prompts import collect_answers
from project_initializer.renderer import render_project
from project_initializer.resources import builtin_pack_dirs

app = typer.Typer(
    name="pypro",
    help="Create production-ready Python web projects from interactive prompts.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pypro {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed pypro version.", callback=_version_callback),
    ] = False,
    target_root: Annotated[
        Path,
        typer.Option("--target-root", help="Directory where the generated project folder is created."),
    ] = Path.cwd(),
) -> None:
    if ctx.invoked_subcommand is None:
        _generate(target_root)
    return None


@app.command()
def new(
    target_root: Annotated[
        Path,
        typer.Option("--target-root", help="Directory where the generated project folder is created."),
    ] = Path.cwd(),
) -> None:
    _generate(target_root)


def _generate(target_root: Path) -> None:
    try:
        raw_answers = collect_answers()
        config = normalize_answers(raw_answers, base_dir=target_root)
        pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
        packs = resolve_packs(config)
        result = render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])
    except ProjectInitializerError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Created project at {result.path}")
    typer.echo("Next steps:")
    typer.echo(f"  cd {result.path}")
    typer.echo("  make venv")
    typer.echo("  make install")
    typer.echo("  make run")
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
pytest tests/test_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/project_initializer/prompts.py src/project_initializer/cli.py tests/test_cli.py
git commit -m "feat: wire interactive project generation"
```

---

### Task 9: End-to-End Test Coverage and Documentation

**Files:**
- Modify: `tests/test_renderer.py`
- Modify: `README.md`

- [ ] **Step 1: Add a Django SQLite golden test**

Append to `tests/test_renderer.py`:

```python
def test_render_builtin_django_sqlite_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Blog Admin",
        project_slug="blog-admin",
        package_name="blog_admin",
        target_dir=tmp_path / "blog-admin",
        project_type=ProjectType.DJANGO,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        use_sqlalchemy=False,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    settings = (config.target_dir / "blog_admin" / "settings.py").read_text(encoding="utf-8")

    assert (config.target_dir / "manage.py").exists()
    assert "django.db.backends.sqlite3" in settings
    assert "rest_framework" not in settings
```

- [ ] **Step 2: Run all tests to verify the new coverage**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 3: Update README with install and usage instructions**

Replace `README.md` with:

````markdown
# Django Project Initializer

Interactive Python web project initializer for Django, Django REST Framework, and FastAPI.

## Install

```bash
pipx install django-project-initializer
```

## Usage

```bash
pypro init
```

The CLI asks for:

- Project name
- Project type: Django, Django with DRF, or FastAPI
- Database: SQLite or PostgreSQL
- FastAPI ORM and migration choices
- Tooling choices: pytest, Ruff, and Docker

Generated projects include:

- `Makefile`
- `.env.example`
- `.gitignore`
- `README.md`
- Runtime dependencies in `requirements.txt`
- Development dependencies in `requirements-dev.txt`

Common generated commands:

```bash
make venv
make install
make run
make test
make lint
make format
make migrate
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```
````

- [ ] **Step 4: Run formatting and full verification**

Run:

```bash
ruff format src tests
ruff check src tests
pytest -v
```

Expected: all commands PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_renderer.py
git commit -m "docs: document project initializer usage"
```

---

### Task 10: Packaging Verification

**Files:**
- Modify only if verification finds a packaging bug.

- [ ] **Step 1: Build the package**

Run:

```bash
python -m pip install build
python -m build
```

Expected: `dist/django_project_initializer-0.1.0-py3-none-any.whl` and source distribution are created.

- [ ] **Step 2: Install the wheel in a temporary virtual environment**

Run:

```bash
python -m venv /tmp/pypro-verify
/tmp/pypro-verify/bin/pip install dist/django_project_initializer-0.1.0-py3-none-any.whl
/tmp/pypro-verify/bin/pypro --version
```

Expected: `pypro 0.1.0`.

- [ ] **Step 3: Generate a project from the installed command**

Run:

```bash
mkdir -p /tmp/pypro-output
printf "Inventory Service\n3\n2\ny\ny\ny\ny\ny\n" | /tmp/pypro-verify/bin/pypro init --target-root /tmp/pypro-output
test -f /tmp/pypro-output/inventory-service/app/main.py
test -f /tmp/pypro-output/inventory-service/alembic.ini
```

Expected: command exits 0 and both generated files exist.

- [ ] **Step 4: Commit packaging fixes if needed**

If Step 1, Step 2, or Step 3 required code changes, commit them:

```bash
git add pyproject.toml src tests README.md
git commit -m "fix: package builtin scaffold resources"
```

If no files changed, skip this commit.

---

## Self-Review

Spec coverage:

- `pipx` install and global command: Task 1 creates package metadata and console command, Task 10 verifies installed command behavior.
- Interactive prompt MVP: Task 8 implements Typer prompts and wires them to generation.
- Django, Django with DRF, and FastAPI stacks: Tasks 5, 6, 7, and 9 cover manifests and templates.
- SQLite and PostgreSQL choices: Tasks 5, 7, and 9 cover database-specific env and generated settings.
- SQLAlchemy and Alembic for FastAPI: Tasks 5 and 6 cover packs, manifests, templates, and golden tests.
- Ruff, pytest, Docker, Makefile, `.env.example`, `.gitignore`, and `README.md`: Tasks 5, 6, 8, and 9 cover generated files and commands.
- Error handling: Tasks 2, 3, 4, and 8 cover invalid names, pack errors, target directory safety, render failures, and CLI error exits.
- Testing strategy: Tasks 1 through 10 include unit tests, resolver tests, renderer tests, golden scaffold tests, and packaging verification.

Placeholder scan:

- The plan contains no deferred implementation markers.
- Every code-changing step names exact paths and provides concrete file content or exact replacement content.

Type consistency:

- `ProjectConfig`, `ToolingOptions`, `ProjectType`, and `Database` are introduced in Task 2 and reused with the same names in later tasks.
- `PackManifest`, `load_pack`, and `resolve_packs` are introduced in Task 3 and reused consistently.
- `render_project` returns `RenderedProject` and accepts `(PackManifest, Path)` tuples consistently after Task 4.
