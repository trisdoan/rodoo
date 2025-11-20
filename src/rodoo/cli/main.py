"""
Desired behaviors of cli
1. No profile, no args → look for config in cwd → if none, exit with help
2. Profile passed → load config → if missing, error
3. Profile + args → load config, prompt to update
4. If no --profile but config exists → prompt to update
5. Args only, no profile, no config → run directly
"""

import typer
from typing import Optional, List
from rodoo.utils.exceptions import UserError
from rodoo.config import APP_HOME
from rodoo.utils.misc import (
    Output,
    perform_update,
    process_cli_args,
    construct_runner,
    handle_exceptions,
)

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
@handle_exceptions
def start(
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    module: Optional[str] = typer.Option(
        None, "--module", "-m", help="Odoo Module name(s), comma-separated"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    db: Optional[str] = typer.Option(None, "--db", "-d", help="Database name"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path to Odoo modules, comma-separated."
    ),
    force_install: Optional[bool] = typer.Option(
        None, "--force-install", help="Force reinstallation of Python dependencies."
    ),
    force_update: Optional[bool] = typer.Option(
        None, "--force-update", help="Force update of Odoo sources."
    ),
):
    """Running Odoo instance"""
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)
    runner = construct_runner(config, args)
    runner.run()


@app.command()
def upgrade(
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    module: Optional[str] = typer.Option(
        None, "--module", "-m", help="Odoo Module name(s), comma-separated"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    db: Optional[str] = typer.Option(None, "--db", "-d", help="Database name"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path to Odoo modules, comma-separated."
    ),
    force_install: Optional[bool] = typer.Option(
        None, "--force-install", help="Force reinstallation of Python dependencies."
    ),
    force_update: Optional[bool] = typer.Option(
        None, "--force-update", help="Force update of Odoo sources."
    ),
):
    """
    Running update Odoo and exist
    """
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)
    try:
        runner = construct_runner(config, args)
        runner.upgrade()
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


@app.command()
def test(
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    module: Optional[str] = typer.Option(
        None, "--module", "-m", help="Odoo Module name(s), comma-separated"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    db: Optional[str] = typer.Option(None, "--db", "-d", help="Database name"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path to Odoo modules, comma-separated."
    ),
    force_install: Optional[bool] = typer.Option(
        None, "--force-install", help="Force reinstallation of Python dependencies."
    ),
    force_update: Optional[bool] = typer.Option(
        None, "--force-update", help="Force update of Odoo sources."
    ),
):
    """
    Running tests
    """
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)
    try:
        runner = construct_runner(config, args)
        runner.run_test()
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


@app.command()
def shell(
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    module: Optional[str] = typer.Option(
        None, "--module", "-m", help="Odoo Module name(s), comma-separated"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    db: Optional[str] = typer.Option(None, "--db", "-d", help="Database name"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path to Odoo modules, comma-separated."
    ),
    force_install: Optional[bool] = typer.Option(
        None, "--force-install", help="Force reinstallation of Python dependencies."
    ),
    force_update: Optional[bool] = typer.Option(
        None, "--force-update", help="Force update of Odoo sources."
    ),
):
    """
    Running Odoo shell
    """
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)
    try:
        runner = construct_runner(config, args)
        runner.run_shell()
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


@app.command()
@handle_exceptions
def translate(
    language: str = typer.Option(..., "--language", "-l", help="Language to translate"),
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    module: Optional[str] = typer.Option(
        None, "--module", "-m", help="Odoo Module name(s), comma-separated"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    db: Optional[str] = typer.Option(None, "--db", "-d", help="Database name"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Path to Odoo modules, comma-separated."
    ),
    force_install: Optional[bool] = typer.Option(
        None, "--force-install", help="Force reinstallation of Python dependencies."
    ),
    force_update: Optional[bool] = typer.Option(
        None, "--force-update", help="Force update of Odoo sources."
    ),
):
    """
    Export translation file for a module
    """
    args = {
        k: v
        for k, v in locals().items()
        if k not in ["profile", "language", "force_install", "force_update"]
        and v is not None
    }
    config = process_cli_args(profile, args)
    runner = construct_runner(config, args)
    runner.export_translation(language)


@app.command()
@handle_exceptions
def update(
    versions: Optional[str] = typer.Option(
        None, "--versions", "-v", help="Odoo version(s) to update, comma-separated"
    ),
):
    """
    Clone and update Odoo src code
    """
    source_path = APP_HOME
    source_path.mkdir(parents=True, exist_ok=True)

    versions_to_update: List[str] = []
    if versions:
        versions_to_update = [v.strip() for v in versions.split(",")]
    else:
        # scan the source directory to find all existing versions to update.
        Output.info(
            f"No versions specified. Scanning {source_path} for existing versions..."
        )
        existing_versions = []
        for item in source_path.iterdir():
            if item.is_dir():
                try:
                    float(item.name)
                    existing_versions.append(item.name)
                except ValueError:
                    # This ignores non-version directories like the 'odoo' and 'enterprise' repos.
                    continue

        versions_to_update = sorted(existing_versions)

    if versions_to_update:
        perform_update(versions_to_update, source_path)
        Output.success("Odoo sources updated successfully.")
    else:
        Output.error(
            f"No installed Odoo versions found in {source_path} to update. "
            "To install a new version, use the --versions flag (e.g., rodoo update --versions 17.0)."
        )


if __name__ == "__main__":
    app()
