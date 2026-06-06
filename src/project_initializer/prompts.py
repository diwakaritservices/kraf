import typer


def collect_answers() -> dict[str, object]:
    project_name = typer.prompt("Project name")
    project_type = _choice_prompt(
        "Project type",
        {
            "1": ("Django", "django"),
            "2": ("Django with DRF", "django_drf"),
            "3": ("FastAPI", "fastapi"),
        },
    )
    database = _choice_prompt(
        "Database",
        {
            "1": ("SQLite", "sqlite"),
            "2": ("PostgreSQL", "postgresql"),
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


def _choice_prompt(label: str, choices: dict[str, tuple[str, str]]) -> str:
    typer.echo(label)
    for key, (display, _value) in choices.items():
        typer.echo(f"  {key}. {display}")

    while True:
        selected = typer.prompt("Select option")
        if selected in choices:
            return choices[selected][1]
        typer.echo(f"Choose one of: {', '.join(choices)}")
