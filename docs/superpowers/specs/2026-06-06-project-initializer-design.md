# Project Initializer Design

## Goal

Build an installable Python CLI utility that helps developers create production-ready Python web projects without repeatedly assembling the same project structure by hand.

The utility will be installed globally with `pipx` and exposed through the `pypro init` command. It will ask interactive questions, compose compatible template packs, render a new project, and generate a consistent Makefile-based developer workflow.

## Scope

The first version targets an interactive CLI only. Reusable config files, Homebrew distribution, and non-interactive generation can be added later, but they are outside the MVP.

The MVP supports these project types:

- Django
- Django with Django REST Framework
- FastAPI

The MVP supports these configurable features:

- SQLite or PostgreSQL database setup
- SQLAlchemy for FastAPI projects
- Alembic migrations for FastAPI projects when SQLAlchemy is selected
- Ruff formatting and linting
- pytest test setup
- Docker setup as an optional feature
- Standard generated files such as `.env.example`, `.gitignore`, `README.md`, and `Makefile`

## User Experience

The user installs the utility with `pipx`:

```bash
pipx install django-project-initializer
```

Then runs:

```bash
pypro init
```

The CLI asks focused questions:

1. Project name
2. Project type: Django, FastAPI, or Django with DRF
3. Database: SQLite or PostgreSQL
4. Stack-specific choices, such as SQLAlchemy and Alembic for FastAPI
5. Tooling choices, such as Docker, pytest, and Ruff

After generation, the CLI prints the created project path and the next commands to run.

## Architecture

The package has four main responsibilities:

- Prompt the user and collect answers.
- Normalize answers into a project configuration object.
- Resolve a compatible set of template packs from that configuration.
- Render and merge pack output into a target project directory.

The generation flow is:

1. Prompt for project choices.
2. Validate and normalize the answers.
3. Resolve base and feature packs.
4. Render files from selected packs with the normalized context.
5. Merge dependencies, dev dependencies, Makefile targets, and environment variables.
6. Write generated files to the target directory.
7. Print next steps.

This separates user interaction from generation logic, which makes the CLI easier to test and lets future config-file support reuse the same generation engine.

## Template Packs

A template pack is a composable unit that contributes project files, dependencies, commands, and compatibility rules. It is not a full starter template by itself.

Example layout:

```text
packs/
  fastapi/
    pack.yaml
    templates/
      app/main.py.j2
      app/api/health.py.j2
  orm-sqlalchemy/
    pack.yaml
    templates/
      app/db/session.py.j2
      app/db/models.py.j2
  migrations-alembic/
    pack.yaml
    templates/
      alembic.ini.j2
      alembic/env.py.j2
```

Each `pack.yaml` can define:

- Files to render
- Runtime dependencies
- Development dependencies
- Makefile targets
- Environment variables for `.env.example`
- Required packs
- Conflicting packs
- Conditions that determine whether the pack is selected

Example compatibility rules:

- `django-drf` requires `django`.
- `migrations-alembic` requires `orm-sqlalchemy`.
- `fastapi` conflicts with `django`.
- `django` and `django-drf` use Django ORM and Django migrations, not SQLAlchemy and Alembic.

## Generated Project Workflow

Generated projects should expose a predictable Makefile interface:

```bash
make venv
make install
make run
make test
make lint
make format
make migrate
```

Individual packs contribute the implementation behind those targets.

For Django:

- `make run` runs the Django development server.
- `make migrate` runs `python manage.py migrate`.
- `make makemigrations` runs `python manage.py makemigrations`.

For FastAPI with SQLAlchemy and Alembic:

- `make run` runs `uvicorn`.
- `make migrate` runs `alembic upgrade head`.
- `make revision` creates a new Alembic migration.

## Error Handling

The CLI should fail early with clear messages when:

- The target directory already exists and is not empty.
- A project name cannot be converted into a valid package name.
- Selected packs have conflicting requirements.
- A pack manifest is invalid.
- A template cannot be rendered.

Errors should explain what failed and, where possible, how the user can recover.

## Testing Strategy

The MVP needs focused tests around the generator contract:

- Prompt answer tests verify that interactive choices become the expected normalized config.
- Pack resolver tests verify required packs, conflicting packs, and stack-specific defaults.
- Rendering tests verify that selected packs produce expected files.
- Golden scaffold tests cover representative combinations:
  - Django with SQLite
  - Django with DRF and PostgreSQL
  - FastAPI with SQLAlchemy and Alembic

The generated projects do not need exhaustive runtime integration tests in the first pass, but generated file structure, dependency lists, and Makefile targets should be checked.

## Initial Non-Goals

- Homebrew distribution
- Web UI
- Reusable YAML config files
- Cloud deployment templates
- Authentication frameworks
- Celery, Redis, or background workers
- Support for every Python package manager

These can be added later through new packs or distribution work after the core generator is stable.

## Approval State

The initial design direction is approved:

- Use `pipx` as the target installation path.
- Build an interactive CLI first.
- Prefer production-ready defaults while keeping choices configurable.
- Use composable template packs rather than one rigid template per stack.
