import sys
from dataclasses import dataclass
from typing import Protocol

import questionary
import typer


@dataclass(frozen=True)
class PromptChoice:
    title: str
    value: str
    description: str


class PromptBackend(Protocol):
    def intro(self) -> None: ...

    def text(self, message: str) -> str: ...

    def select(self, message: str, choices: tuple[PromptChoice, ...]) -> str: ...

    def confirm(self, message: str, *, default: bool) -> bool: ...


PROJECT_TYPE_CHOICES = (
    PromptChoice("Django", "django", "Full Django project"),
    PromptChoice("Django + DRF", "django_drf", "Django REST API project"),
    PromptChoice("FastAPI", "fastapi", "Async API service"),
)

DATABASE_CHOICES = (
    PromptChoice("No database", "none", "Service without ORM setup"),
    PromptChoice("SQLite", "sqlite", "Local file database"),
    PromptChoice("PostgreSQL", "postgresql", "Production-style database"),
)


def collect_answers(backend: PromptBackend | None = None) -> dict[str, object]:
    prompt = backend or _default_backend()
    prompt.intro()

    project_name = prompt.text("Project name")
    project_type = prompt.select("Choose a project type", PROJECT_TYPE_CHOICES)
    database = prompt.select("Choose a database", DATABASE_CHOICES)

    use_sqlalchemy = False
    use_alembic = False
    if project_type == "fastapi" and database != "none":
        use_sqlalchemy = prompt.confirm("Use SQLAlchemy ORM?", default=True)
        if use_sqlalchemy:
            use_alembic = prompt.confirm("Use Alembic migrations?", default=True)

    return {
        "project_name": project_name,
        "project_type": project_type,
        "database": database,
        "use_sqlalchemy": use_sqlalchemy,
        "use_alembic": use_alembic,
        "use_pytest": prompt.confirm("Include pytest?", default=True),
        "use_ruff": prompt.confirm("Include Ruff?", default=True),
        "use_docker": prompt.confirm("Include Docker?", default=True),
    }


def _default_backend() -> PromptBackend:
    if sys.stdin.isatty() and sys.stdout.isatty():
        return QuestionaryPromptBackend()
    return PlainPromptBackend()


class QuestionaryPromptBackend:
    def __init__(self) -> None:
        self._style = questionary.Style(
            [
                ("qmark", "fg:#7dd3fc bold"),
                ("question", "bold"),
                ("answer", "fg:#86efac bold"),
                ("pointer", "fg:#7dd3fc bold"),
                ("highlighted", "fg:#7dd3fc bold"),
                ("selected", "fg:#86efac"),
                ("instruction", "fg:#9ca3af"),
                ("text", "fg:#e5e7eb"),
                ("disabled", "fg:#6b7280 italic"),
            ]
        )

    def intro(self) -> None:
        questionary.print("kraf", style="bold fg:#7dd3fc")
        questionary.print("Production-ready Python project scaffolding", style="fg:#9ca3af")
        questionary.print("")

    def text(self, message: str) -> str:
        return _require_answer(
            questionary.text(message, qmark=">", style=self._style).unsafe_ask(),
            message,
        )

    def select(self, message: str, choices: tuple[PromptChoice, ...]) -> str:
        return _require_answer(
            questionary.select(
                message,
                choices=[
                    questionary.Choice(
                        title=choice.title,
                        value=choice.value,
                        description=choice.description,
                    )
                    for choice in choices
                ],
                qmark=">",
                pointer=">",
                style=self._style,
                show_description=True,
                instruction="Use arrows, then Enter",
            ).unsafe_ask(),
            message,
        )

    def confirm(self, message: str, *, default: bool) -> bool:
        answer = questionary.confirm(
            message,
            default=default,
            qmark=">",
            style=self._style,
        ).unsafe_ask()
        if answer is None:
            raise typer.Abort()
        return bool(answer)


class PlainPromptBackend:
    def intro(self) -> None:
        typer.echo("kraf")
        typer.echo("Production-ready Python project scaffolding")
        typer.echo()

    def text(self, message: str) -> str:
        return typer.prompt(message)

    def select(self, message: str, choices: tuple[PromptChoice, ...]) -> str:
        typer.echo(message)
        indexed_choices = {str(index): choice for index, choice in enumerate(choices, start=1)}
        width = max(len(choice.title) for choice in choices)
        for key, choice in indexed_choices.items():
            typer.echo(f"  {key}. {choice.title.ljust(width)}  {choice.description}")

        while True:
            selected = typer.prompt(f"Select option [1-{len(choices)}]")
            if selected in indexed_choices:
                return indexed_choices[selected].value
            typer.echo(f"Choose one of: {', '.join(indexed_choices)}")

    def confirm(self, message: str, *, default: bool) -> bool:
        return typer.confirm(message, default=default)


def _require_answer(answer: object, message: str) -> str:
    if answer is None:
        raise typer.Abort()
    if not isinstance(answer, str):
        return str(answer)
    if not answer.strip():
        raise typer.BadParameter(f"{message} is required.")
    return answer
