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
    name="project-init",
    help="Create production-ready Python web projects from interactive prompts.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"project-init {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the installed project-init version.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    target_root: Annotated[
        Path | None,
        typer.Option(
            "--target-root",
            help="Directory where the generated project folder is created.",
        ),
    ] = None,
) -> None:
    if ctx.invoked_subcommand is None:
        _generate(target_root or Path.cwd())
    return None


@app.command()
def new(
    target_root: Annotated[
        Path | None,
        typer.Option(
            "--target-root",
            help="Directory where the generated project folder is created.",
        ),
    ] = None,
) -> None:
    _generate(target_root or Path.cwd())


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
