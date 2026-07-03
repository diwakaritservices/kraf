import subprocess
import sys
from pathlib import Path

import pytest

from project_initializer.config import (
    Database,
    OrmChoice,
    ProjectConfig,
    ProjectType,
    ToolingOptions,
)
from project_initializer.errors import RenderError
from project_initializer.pack import PackManifest, resolve_packs
from project_initializer.renderer import RenderedProject, render_project
from project_initializer.resources import builtin_pack_dirs


def _config(tmp_path: Path) -> ProjectConfig:
    return ProjectConfig(
        project_name="Customer API",
        project_slug="customer-api",
        package_name="customer_api",
        target_dir=tmp_path / "customer-api",
        project_type=ProjectType.FASTAPI,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        orm=OrmChoice.NONE,
        use_alembic=False,
    )


def test_render_project_writes_templates_and_merged_files(tmp_path: Path):
    pack_root = tmp_path / "packs"
    pack_dir = pack_root / "fastapi"
    template_dir = pack_dir / "templates" / "app"
    template_dir.mkdir(parents=True)
    (template_dir / "main.py.j2").write_text(
        'APP_NAME = "{{ project.project_name }}"\n',
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
        'APP_NAME = "Customer API"\n'
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


def test_render_project_rejects_unsafe_destination(tmp_path: Path):
    pack_dir = tmp_path / "packs" / "unsafe"
    template_dir = pack_dir / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / "content.txt.j2").write_text("data\n", encoding="utf-8")
    pack = PackManifest(
        name="unsafe",
        files=(("content.txt.j2", "../outside.txt"),),
    )

    with pytest.raises(RenderError, match="unsafe template destination"):
        render_project(_config(tmp_path), [(pack, pack_dir)])


def test_render_project_rejects_empty_rendered_destination(tmp_path: Path):
    pack_dir = tmp_path / "packs" / "unsafe"
    template_dir = pack_dir / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / "content.txt.j2").write_text("data\n", encoding="utf-8")
    pack = PackManifest(
        name="unsafe",
        files=(("content.txt.j2", "{{ '' }}"),),
    )

    with pytest.raises(RenderError, match="unsafe template destination"):
        render_project(_config(tmp_path), [(pack, pack_dir)])


def test_render_builtin_fastapi_sqlalchemy_alembic_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config = ProjectConfig(
        project_name="Inventory Service",
        project_slug="inventory-service",
        package_name="inventory_service",
        target_dir=tmp_path / "inventory-service",
        project_type=ProjectType.FASTAPI,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True),
        orm=OrmChoice.SQLALCHEMY,
        use_alembic=True,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    assert (config.target_dir / "app" / "main.py").exists()
    assert (config.target_dir / "app" / "db" / "session.py").exists()
    assert (config.target_dir / "app" / "db" / "base.py").exists()
    assert (config.target_dir / "alembic.ini").exists()
    script_template = config.target_dir / "alembic" / "script.py.mako"
    revision_helper = config.target_dir / "scripts" / "create_migration.py"
    assert script_template.exists()
    assert revision_helper.exists()
    assert (config.target_dir / "Dockerfile").exists()
    compose = (config.target_dir / "docker-compose.yml").read_text(encoding="utf-8")
    env = (config.target_dir / ".env.example").read_text(encoding="utf-8")
    makefile = (config.target_dir / "Makefile").read_text(encoding="utf-8")
    requirements = (config.target_dir / "requirements.txt").read_text(encoding="utf-8")
    assert "apt-get install" in (config.target_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "make" in (config.target_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "python-dotenv" in requirements
    assert "db:" in compose
    assert "image: postgres:16-alpine" in compose
    assert "depends_on:" in compose
    assert "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/app" in env
    assert "DATABASE_URL: postgresql://postgres:postgres@db:5432/app" in compose
    assert "make run" in (config.target_dir / "README.md").read_text(encoding="utf-8")
    assert "ifeq ($(OS),Windows_NT)" in makefile
    assert "PYTHON ?= python3" in makefile
    assert "PYTHON ?= python" in makefile
    assert "install: .venv/pyvenv.cfg" in makefile
    assert "docker-up:\n\tdocker compose up --build" in makefile
    assert "$(VENV_PYTHON) -m pip install" in makefile
    assert "$(VENV_PYTHON) -m alembic upgrade head" in makefile
    alembic_revision_command = "$(VENV_PYTHON) scripts/create_migration.py"
    assert (
        f"migrations: .venv/pyvenv.cfg\n\t{alembic_revision_command}" in makefile
    )
    assert f"revision: .venv/pyvenv.cfg\n\t{alembic_revision_command}" in makefile
    assert '-m "change"' not in makefile
    assert "No migrations configured" not in makefile

    script_template_content = script_template.read_text(encoding="utf-8")
    assert "${message}" in script_template_content
    assert '${upgrades if upgrades else "pass"}' in script_template_content
    assert '${downgrades if downgrades else "pass"}' in script_template_content

    commands: list[tuple[list[str], bool]] = []
    monkeypatch.setattr("builtins.input", lambda _prompt: "create inventory table")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, check: commands.append((command, check)),
    )
    helper_namespace = {"__name__": "generated_migration_helper"}
    exec(
        compile(
            revision_helper.read_text(encoding="utf-8"),
            str(revision_helper),
            "exec",
        ),
        helper_namespace,
    )

    helper_namespace["main"]()

    assert commands == [
        (
            [
                sys.executable,
                "-m",
                "alembic",
                "revision",
                "--autogenerate",
                "-m",
                "create inventory table",
            ],
            True,
        )
    ]
    session = (config.target_dir / "app" / "db" / "session.py").read_text(encoding="utf-8")
    alembic_env = (config.target_dir / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "from dotenv import load_dotenv" in session
    assert "from collections.abc import Generator" in session
    assert "from sqlalchemy.orm import Session, sessionmaker" in session
    assert "load_dotenv()" in session
    assert "def get_db() -> Generator[Session, None, None]:" in session
    assert "db = SessionLocal()" in session
    assert "yield db" in session
    assert "db.close()" in session
    assert "from dotenv import load_dotenv" in alembic_env
    assert "load_dotenv()" in alembic_env
    base_model = (config.target_dir / "app" / "db" / "base.py").read_text(encoding="utf-8")
    models = (config.target_dir / "app" / "db" / "models.py").read_text(encoding="utf-8")
    main_py = (config.target_dir / "app" / "main.py").read_text(encoding="utf-8")
    users_api = (config.target_dir / "app" / "api" / "users.py").read_text(encoding="utf-8")
    assert "class BaseModel(Base):" in base_model
    assert "deleted_at" in base_model
    assert "is_deleted" not in base_model
    assert 'class User(BaseModel):' in models
    assert '__tablename__ = "users"' in models
    assert "bcrypt" in requirements
    assert "users_router" in main_py
    assert 'prefix="/users"' in users_api
    assert "hash_password" in users_api
    alembic_script_template = (config.target_dir / "alembic" / "script.py.mako").read_text(
        encoding="utf-8"
    )
    assert "import sqlmodel" not in alembic_script_template
    assert "% if project.orm" not in alembic_script_template


def test_render_builtin_fastapi_sqlmodel_alembic_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Inventory Service",
        project_slug="inventory-service",
        package_name="inventory_service",
        target_dir=tmp_path / "inventory-service",
        project_type=ProjectType.FASTAPI,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True),
        orm=OrmChoice.SQLMODEL,
        use_alembic=True,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    requirements = (config.target_dir / "requirements.txt").read_text(encoding="utf-8")
    base_model = (config.target_dir / "app" / "db" / "base.py").read_text(encoding="utf-8")
    models = (config.target_dir / "app" / "db" / "models.py").read_text(encoding="utf-8")
    main_py = (config.target_dir / "app" / "main.py").read_text(encoding="utf-8")
    users_api = (config.target_dir / "app" / "api" / "users.py").read_text(encoding="utf-8")
    alembic_env = (config.target_dir / "alembic" / "env.py").read_text(encoding="utf-8")
    alembic_script_template = (config.target_dir / "alembic" / "script.py.mako").read_text(
        encoding="utf-8"
    )

    assert "sqlmodel" in requirements
    assert "bcrypt" in requirements
    assert "from sqlmodel import Field, SQLModel" in base_model
    assert "sa_type=Uuid" in base_model
    assert "sa_column=Column" not in base_model
    assert "class User(BaseModel, table=True):" in models
    assert "__tablename__" not in models
    assert "users_router" in main_py
    assert 'prefix="/users"' in users_api
    assert "from sqlmodel import SQLModel" in alembic_env
    assert "target_metadata = SQLModel.metadata" in alembic_env
    assert "import sqlmodel" in alembic_script_template
    assert "% if project.orm" not in alembic_script_template


def test_sqlmodel_base_allows_multiple_table_models(tmp_path: Path):
    pytest.importorskip("sqlmodel")

    import importlib.util
    import sys

    project_dir = tmp_path / "inventory-service"
    config = ProjectConfig(
        project_name="Inventory Service",
        project_slug="inventory-service",
        package_name="inventory_service",
        target_dir=project_dir,
        project_type=ProjectType.FASTAPI,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=False, use_ruff=False),
        orm=OrmChoice.SQLMODEL,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)
    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    (project_dir / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project_dir / "app" / "db" / "__init__.py").write_text("", encoding="utf-8")
    (project_dir / "app" / "db" / "models.py").write_text(
        """from sqlmodel import Field

from app.db.base import BaseModel


class Employee(BaseModel, table=True):
    name: str = Field(index=True)


class Department(BaseModel, table=True):
    name: str = Field(index=True)
""",
        encoding="utf-8",
    )

    sys.path.insert(0, str(project_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "generated_models",
            project_dir / "app" / "db" / "models.py",
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(project_dir))

    from sqlmodel import SQLModel

    table_names = set(SQLModel.metadata.tables)
    assert "employee" in table_names
    assert "department" in table_names


def test_render_builtin_django_drf_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Customer API",
        project_slug="customer-api",
        package_name="customer_api",
        target_dir=tmp_path / "customer-api",
        project_type=ProjectType.DJANGO_DRF,
        database=Database.POSTGRESQL,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        orm=OrmChoice.NONE,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    assert (config.target_dir / "manage.py").exists()
    assert (config.target_dir / "customer_api" / "__init__.py").exists()
    assert (config.target_dir / "customer_api" / "settings.py").exists()
    assert (config.target_dir / "core" / "models.py").exists()
    assert (config.target_dir / "core" / "apps.py").exists()
    assert (config.target_dir / "core" / "migrations" / "0001_initial.py").exists()
    assert (config.target_dir / "api" / "__init__.py").exists()
    assert (config.target_dir / "api" / "views.py").exists()
    settings = (config.target_dir / "customer_api" / "settings.py").read_text(encoding="utf-8")
    assert "djangorestframework" in (config.target_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert "python-dotenv" in (config.target_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )
    env = (config.target_dir / ".env.example").read_text(encoding="utf-8")
    makefile = (config.target_dir / "Makefile").read_text(encoding="utf-8")
    assert "from dotenv import load_dotenv" in settings
    assert 'load_dotenv(BASE_DIR / ".env")' in settings
    assert "DJANGO_SECRET_KEY=change-me" in env
    assert "DJANGO_DEBUG=true" in env
    assert "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1" in env
    assert "DATABASE_URL=" not in env
    assert "POSTGRES_DB=app" in env
    assert "POSTGRES_USER=postgres" in env
    assert "POSTGRES_PASSWORD=postgres" in env
    assert "POSTGRES_HOST=localhost" in env
    assert "POSTGRES_PORT=5432" in env
    assert "$(VENV_PYTHON) manage.py migrate" in makefile
    assert (
        "migrations: .venv/pyvenv.cfg\n\t$(VENV_PYTHON) manage.py makemigrations core"
        in makefile
    )
    assert (
        "makemigrations: .venv/pyvenv.cfg\n\t$(VENV_PYTHON) manage.py makemigrations core"
        in makefile
    )
    assert "No migrations configured" not in makefile
    base_model = (config.target_dir / "core" / "models.py").read_text(encoding="utf-8")
    assert "class BaseModel(models.Model):" in base_model
    assert "class User(AbstractBaseUser, PermissionsMixin, BaseModel):" in base_model
    assert "class UserManager(BaseUserManager):" in base_model
    assert 'USERNAME_FIELD = "email"' in base_model
    assert 'AUTH_USER_MODEL = "core.User"' in settings
    assert "models.UUIDField" in base_model
    assert "deleted_at" in base_model
    assert "is_deleted" not in base_model
    assert "abstract = True" in base_model
    assert (config.target_dir / "api" / "serializers.py").exists()
    api_urls = (config.target_dir / "api" / "urls.py").read_text(encoding="utf-8")
    api_views = (config.target_dir / "api" / "views.py").read_text(encoding="utf-8")
    api_serializers = (config.target_dir / "api" / "serializers.py").read_text(encoding="utf-8")
    assert "DefaultRouter" in api_urls
    assert "users" in api_urls
    assert "UserViewSet" in api_views
    assert "UserSerializer" in api_serializers


def test_render_builtin_django_project_omits_drf_imports(tmp_path: Path):
    config = ProjectConfig(
        project_name="Blog Admin",
        project_slug="blog-admin",
        package_name="blog_admin",
        target_dir=tmp_path / "blog-admin",
        project_type=ProjectType.DJANGO,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        orm=OrmChoice.NONE,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    settings = (config.target_dir / "blog_admin" / "settings.py").read_text(encoding="utf-8")
    urls = (config.target_dir / "blog_admin" / "urls.py").read_text(encoding="utf-8")

    assert "rest_framework" not in settings
    assert '"api"' not in settings
    assert "include" not in urls


def test_render_builtin_django_sqlite_project(tmp_path: Path):
    config = ProjectConfig(
        project_name="Blog Admin",
        project_slug="blog-admin",
        package_name="blog_admin",
        target_dir=tmp_path / "blog-admin",
        project_type=ProjectType.DJANGO,
        database=Database.SQLITE,
        tooling=ToolingOptions(use_docker=False, use_pytest=True, use_ruff=True),
        orm=OrmChoice.NONE,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    settings = (config.target_dir / "blog_admin" / "settings.py").read_text(encoding="utf-8")

    assert (config.target_dir / "manage.py").exists()
    assert (config.target_dir / "core" / "models.py").exists()
    assert (config.target_dir / "core" / "migrations" / "0001_initial.py").exists()
    assert "django.db.backends.sqlite3" in settings
    assert "rest_framework" not in settings


def test_render_builtin_django_project_without_database(tmp_path: Path):
    config = ProjectConfig(
        project_name="Blog Admin",
        project_slug="blog-admin",
        package_name="blog_admin",
        target_dir=tmp_path / "blog-admin",
        project_type=ProjectType.DJANGO,
        database=Database.NONE,
        tooling=ToolingOptions(use_docker=True, use_pytest=True, use_ruff=True),
        orm=OrmChoice.NONE,
        use_alembic=False,
    )
    pack_dirs = {pack_dir.name: pack_dir for pack_dir in builtin_pack_dirs()}
    packs = resolve_packs(config)

    render_project(config, [(pack, pack_dirs[pack.name]) for pack in packs])

    settings = (config.target_dir / "blog_admin" / "settings.py").read_text(encoding="utf-8")
    makefile = (config.target_dir / "Makefile").read_text(encoding="utf-8")
    compose = (config.target_dir / "docker-compose.yml").read_text(encoding="utf-8")
    env = (config.target_dir / ".env.example").read_text(encoding="utf-8")
    readme = (config.target_dir / "README.md").read_text(encoding="utf-8")

    assert "django.db.backends.dummy" in settings
    assert "DJANGO_SECRET_KEY=change-me" in env
    assert "DJANGO_DEBUG=true" in env
    assert "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1" in env
    assert '"core"' not in settings
    assert not (config.target_dir / "core").exists()
    assert "DATABASE_URL=" not in env
    assert "POSTGRES_" not in env
    assert "migrate:" not in makefile
    assert "migrations:" not in makefile
    assert "makemigrations:" not in makefile
    assert "revision:" not in makefile
    assert "No migrations configured" not in makefile
    assert "make migrate" not in readme
    assert "make migrations" not in readme
    assert "db:" not in compose
