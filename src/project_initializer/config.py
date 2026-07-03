from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from project_initializer.errors import InvalidProjectNameError
from project_initializer.name_utils import normalize_package_name, normalize_project_slug


class ProjectType(StrEnum):
    DJANGO = "django"
    DJANGO_DRF = "django_drf"
    FASTAPI = "fastapi"


class Database(StrEnum):
    NONE = "none"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class OrmChoice(StrEnum):
    NONE = "none"
    SQLALCHEMY = "sqlalchemy"
    SQLMODEL = "sqlmodel"


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
    orm: OrmChoice
    use_alembic: bool


def normalize_answers(raw_answers: dict[str, Any], base_dir: Path | None = None) -> ProjectConfig:
    raw_project_name = raw_answers.get("project_name")
    if raw_project_name is None:
        raise InvalidProjectNameError("Project name is required.")
    if not isinstance(raw_project_name, str):
        raise InvalidProjectNameError("Project name must be text.")

    project_name = raw_project_name.strip()
    project_type = ProjectType(str(raw_answers["project_type"]))
    database = Database(str(raw_answers["database"]))
    package_name = normalize_package_name(project_name)
    project_slug = normalize_project_slug(project_name)
    target_root = base_dir or Path.cwd()

    orm = OrmChoice(str(raw_answers.get("orm", OrmChoice.NONE)))
    use_alembic = bool(raw_answers.get("use_alembic", False))
    if project_type is not ProjectType.FASTAPI or database is Database.NONE:
        orm = OrmChoice.NONE
        use_alembic = False
    elif orm is OrmChoice.NONE:
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
        orm=orm,
        use_alembic=use_alembic,
    )
