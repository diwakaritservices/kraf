from typer.testing import CliRunner

from project_initializer.cli import app


def test_version_command_displays_package_version():
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "kraf 0.1.4" in result.stdout


def test_init_command_generates_fastapi_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["init", "--target-root", str(tmp_path)],
        input="Inventory Service\n3\n3\n2\ny\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert (tmp_path / "inventory-service" / "app" / "api" / "users.py").exists()
    assert "Created project" in result.stdout


def test_init_command_generates_fastapi_project_without_database(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["init", "--target-root", str(tmp_path)],
        input="Inventory Service\n3\n1\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert not (tmp_path / "inventory-service" / "app" / "db").exists()
    main_py = (tmp_path / "inventory-service" / "app" / "main.py").read_text(encoding="utf-8")
    assert "users_router" not in main_py
    assert "Created project" in result.stdout


def test_root_command_no_longer_generates_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(app, [])

    assert result.exit_code != 0
    assert not (tmp_path / "inventory-service").exists()
    assert "Usage:" in result.stdout
    assert "init" in result.stdout
