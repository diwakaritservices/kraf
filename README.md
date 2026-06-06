# pypro

Interactive Python web project initializer for Django, Django REST Framework, and FastAPI.

## Install

```bash
pipx install git+https://github.com/abhidiwakar/pypro.git
```

## Usage

```bash
pypro init
```

The CLI asks for:

- Project name
- Project type: Django, Django with DRF, or FastAPI
- Database: SQLite or PostgreSQL
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
make migrate
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src tests
```
