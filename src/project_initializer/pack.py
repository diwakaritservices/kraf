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
        "migrations_alembic": PackManifest(name="migrations_alembic", requires=("orm_sqlalchemy",)),
        "tooling_pytest": PackManifest(name="tooling_pytest"),
        "tooling_ruff": PackManifest(name="tooling_ruff"),
        "docker": PackManifest(name="docker"),
    }
