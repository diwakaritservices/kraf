# kraf

Interactive Python web project initializer for Django, Django REST Framework, and FastAPI.

## Install

```bash
pipx install kraf
```

## Usage

```bash
kraf init
```

The CLI asks for:

- Project name
- Project type: Django, Django with DRF, or FastAPI
- Database: no database, SQLite, or PostgreSQL
- FastAPI ORM and migration choices
- Tooling choices: pytest, Ruff, and Docker

Generated projects include:

- `Makefile`
- `.env.example`
- `.gitignore`
- `README.md`
- Runtime dependencies in `requirements.txt`
- Development dependencies in `requirements-dev.txt`

Common generated commands:

```bash
make venv
make install
make run
make test
make lint
make format
make migrations
make migrate
```

Migration commands are generated only for database-backed projects. `make migrations`
creates a migration, while `make migrate` applies migrations. Alembic projects also
provide `make revision`; both revision creation commands prompt for a migration message.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```
