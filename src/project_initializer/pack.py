from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from project_initializer.config import Database, OrmChoice, ProjectConfig, ProjectType
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
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PackError(f"Pack at {pack_dir} is missing pack.yaml.") from exc
    except yaml.YAMLError as exc:
        raise PackError(f"Pack at {pack_dir} has invalid YAML: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise PackError(f"Pack at {pack_dir} manifest must be a mapping.")
    if "name" not in raw:
        raise PackError(f"Pack at {pack_dir} is missing required field 'name'.")

    return _manifest_from_mapping(raw, pack_dir)


def _manifest_from_mapping(raw: Mapping[str, Any], pack_dir: Path) -> PackManifest:
    name = _require_non_empty_string(raw, "name", pack_dir)
    files = _files_from_mapping(raw, pack_dir)

    return PackManifest(
        name=name,
        dependencies=_string_tuple_field(raw, "dependencies", pack_dir),
        dev_dependencies=_string_tuple_field(raw, "dev_dependencies", pack_dir),
        files=files,
        make_targets=_string_mapping_field(raw, "make_targets", pack_dir),
        env=_string_mapping_field(raw, "env", pack_dir),
        requires=_string_tuple_field(raw, "requires", pack_dir),
        conflicts=_string_tuple_field(raw, "conflicts", pack_dir),
    )


def _require_non_empty_string(
    raw: Mapping[str, Any], field_name: str, pack_dir: Path
) -> str:
    value = raw[field_name]
    if not isinstance(value, str) or not value:
        raise PackError(
            f"Pack at {pack_dir} has invalid field '{field_name}'; expected a non-empty string."
        )
    return value


def _string_tuple_field(
    raw: Mapping[str, Any], field_name: str, pack_dir: Path
) -> tuple[str, ...]:
    value = raw.get(field_name, [])
    if not isinstance(value, (list, tuple)):
        raise PackError(f"Pack at {pack_dir} field '{field_name}' must be a list of strings.")
    if not all(isinstance(item, str) for item in value):
        raise PackError(f"Pack at {pack_dir} field '{field_name}' must be a list of strings.")
    return tuple(value)


def _string_mapping_field(
    raw: Mapping[str, Any], field_name: str, pack_dir: Path
) -> dict[str, str]:
    value = raw.get(field_name, {})
    if not isinstance(value, Mapping):
        raise PackError(
            f"Pack at {pack_dir} field '{field_name}' must be a mapping of strings to strings."
        )
    if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
        raise PackError(
            f"Pack at {pack_dir} field '{field_name}' must be a mapping of strings to strings."
        )
    return dict(value)


def _files_from_mapping(
    raw: Mapping[str, Any], pack_dir: Path
) -> tuple[tuple[str, str], ...]:
    value = raw.get("files", [])
    if not isinstance(value, (list, tuple)):
        raise PackError(f"Pack at {pack_dir} field 'files' must be a list of file mappings.")

    files = []
    for file_entry in value:
        if not isinstance(file_entry, Mapping):
            raise PackError(f"Pack at {pack_dir} field 'files' must contain file mappings.")
        source = file_entry.get("source")
        destination = file_entry.get("destination")
        if not isinstance(source, str) or not source:
            raise PackError(f"Pack at {pack_dir} has a file entry without source and destination.")
        if not isinstance(destination, str) or not destination:
            raise PackError(f"Pack at {pack_dir} has a file entry without source and destination.")
        files.append((str(source), str(destination)))

    return tuple(files)


def resolve_packs(
    config: ProjectConfig,
    *,
    available_packs: dict[str, PackManifest] | None = None,
    explicit_names: list[str] | None = None,
) -> list[PackManifest]:
    pack_map = _default_pack_manifest_map() if available_packs is None else available_packs
    names = _pack_names_for_config(config) if explicit_names is None else explicit_names

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

    if config.project_type in {ProjectType.DJANGO, ProjectType.DJANGO_DRF} and (
        config.database is not Database.NONE
    ):
        names.append("django_models")

    if config.orm is OrmChoice.SQLALCHEMY and config.database is not Database.NONE:
        names.append("orm_sqlalchemy")
    elif config.orm is OrmChoice.SQLMODEL and config.database is not Database.NONE:
        names.append("orm_sqlmodel")
    if config.use_alembic and config.database is not Database.NONE:
        names.append("migrations_alembic")
    if config.tooling.use_pytest:
        names.append("tooling_pytest")
    if config.tooling.use_ruff:
        names.append("tooling_ruff")
    if config.tooling.use_docker:
        names.append("docker")

    return names


def _default_pack_manifest_map() -> dict[str, PackManifest]:
    from project_initializer.resources import builtin_pack_dirs

    manifests = [load_pack(pack_dir) for pack_dir in builtin_pack_dirs()]
    return {manifest.name: manifest for manifest in manifests}
