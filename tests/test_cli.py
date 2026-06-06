from typer.testing import CliRunner

from project_initializer.cli import app


def test_version_command_displays_package_version():
    runner = CliRunner()

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "project-init 0.1.0" in result.stdout


def test_new_command_generates_fastapi_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["new", "--target-root", str(tmp_path)],
        input="Inventory Service\n3\n2\ny\ny\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert "Created project" in result.stdout


def test_root_command_generates_fastapi_project(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--target-root", str(tmp_path)],
        input="Inventory Service\n3\n2\ny\ny\ny\ny\ny\n",
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "inventory-service" / "app" / "main.py").exists()
    assert "Created project" in result.stdout
