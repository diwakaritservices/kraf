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
