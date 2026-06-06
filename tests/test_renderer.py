from pathlib import Path

import pytest

from project_initializer.config import Database, ProjectConfig, ProjectType, ToolingOptions
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
        use_sqlalchemy=False,
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
    assert "apt-get install" in (config.target_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "make" in (config.target_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "make run" in (config.target_dir / "README.md").read_text(encoding="utf-8")
    assert "alembic upgrade head" in (config.target_dir / "Makefile").read_text(
        encoding="utf-8"
    )


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
    assert (config.target_dir / "customer_api" / "__init__.py").exists()
    assert (config.target_dir / "customer_api" / "settings.py").exists()
    assert (config.target_dir / "api" / "__init__.py").exists()
    assert (config.target_dir / "api" / "views.py").exists()
    assert "djangorestframework" in (config.target_dir / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert "python manage.py migrate" in (config.target_dir / "Makefile").read_text(
        encoding="utf-8"
    )


def test_render_builtin_django_project_omits_drf_imports(tmp_path: Path):
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
    urls = (config.target_dir / "blog_admin" / "urls.py").read_text(encoding="utf-8")

    assert "rest_framework" not in settings
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
