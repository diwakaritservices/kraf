from project_initializer.prompts import PromptChoice, collect_answers


class FakePromptBackend:
    def __init__(self, answers: list[object]):
        self.answers = answers
        self.intro_calls = 0
        self.text_calls: list[str] = []
        self.select_calls: list[tuple[str, tuple[PromptChoice, ...]]] = []
        self.confirm_calls: list[tuple[str, bool]] = []

    def intro(self) -> None:
        self.intro_calls += 1

    def text(self, message: str) -> str:
        self.text_calls.append(message)
        return str(self.answers.pop(0))

    def select(self, message: str, choices: tuple[PromptChoice, ...]) -> str:
        self.select_calls.append((message, choices))
        return str(self.answers.pop(0))

    def confirm(self, message: str, *, default: bool) -> bool:
        self.confirm_calls.append((message, default))
        return bool(self.answers.pop(0))


def test_collect_answers_uses_polished_prompt_backend():
    backend = FakePromptBackend(
        [
            "Inventory Service",
            "fastapi",
            "postgresql",
            True,
            True,
            True,
            True,
            True,
        ]
    )

    answers = collect_answers(backend=backend)

    assert answers == {
        "project_name": "Inventory Service",
        "project_type": "fastapi",
        "database": "postgresql",
        "use_sqlalchemy": True,
        "use_alembic": True,
        "use_pytest": True,
        "use_ruff": True,
        "use_docker": True,
    }
    assert backend.intro_calls == 1
    assert backend.text_calls == ["Project name"]
    assert backend.select_calls[0][0] == "Choose a project type"
    assert backend.select_calls[0][1] == (
        PromptChoice("Django", "django", "Full Django project"),
        PromptChoice("Django + DRF", "django_drf", "Django REST API project"),
        PromptChoice("FastAPI", "fastapi", "Async API service"),
    )
    assert backend.select_calls[1][0] == "Choose a database"
    assert backend.select_calls[1][1] == (
        PromptChoice("No database", "none", "Service without ORM setup"),
        PromptChoice("SQLite", "sqlite", "Local file database"),
        PromptChoice("PostgreSQL", "postgresql", "Production-style database"),
    )


def test_collect_answers_skips_orm_prompts_without_database():
    backend = FakePromptBackend(
        [
            "Inventory Service",
            "fastapi",
            "none",
            True,
            True,
            True,
        ]
    )

    answers = collect_answers(backend=backend)

    assert answers["database"] == "none"
    assert answers["use_sqlalchemy"] is False
    assert answers["use_alembic"] is False
    assert backend.confirm_calls == [
        ("Include pytest?", True),
        ("Include Ruff?", True),
        ("Include Docker?", True),
    ]
