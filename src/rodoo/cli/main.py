"""
Desired behaviors of cli
1. No profile, no args → look for config in cwd → if none, exit with help
2. Profile passed → load config → if missing, error
3. Profile + args → load config, prompt to update
4. If no --profile but config exists → prompt to update
5. Args only, no profile, no config → run directly
"""

from pathlib import Path
import typer
from typing import Optional, List
from rodoo.output import Output
from rodoo.exceptions import UserError
from rodoo.utils import perform_update, process_cli_args, construct_runner


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
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
):
    """Running Odoo instance"""
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)

    try:
        runner = construct_runner(config, args)
        runner.run()
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


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


# FIXME: error with filestore, need to understand the problem
@app.command()
def restore(
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Profile name to run Odoo"
    ),
    db: str = typer.Option(None, "--db", "-d", help="Database name to restore to"),
    dump_file: Path = typer.Option(
        "dump.sql", "--dump-file", "-f", help="Path to dump file to restore from"
    ),
    version: Optional[float] = typer.Option(
        None, "--version", "-v", help="Odoo version"
    ),
    python_version: Optional[str] = typer.Option(None, "--python", "-py"),
    copy: bool = typer.Option(
        False, "--copy", help="Create a copy of the database for restore"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force restore even if database exists (will be dropped)"
    ),
):
    """Restore a database from a file."""
    if copy and not db:
        Output.error("The --copy flag requires the --db option to be specified.")
        raise typer.Exit(1)

    args = {
        k: v
        for k, v in locals().items()
        if k not in ["profile", "dump_file", "copy", "force"] and v is not None
    }

    target_db = db
    if copy:
        target_db = f"{db}_copy"
        Output.info(f"Restoring to a new database: {target_db}")
        args["db"] = target_db

    config = process_cli_args(profile, args)

    try:
        runner = construct_runner(config, args)

        if not target_db:
            target_db = runner.db

        runner.restore(target_db, dump_file, copy, force)
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


@app.command()
def update(
    versions: Optional[str] = typer.Option(
        None, "--versions", "-v", help="Odoo version(s) to update, comma-separated"
    ),
):
    """
    Clone and update Odoo src code
    """
    source_path = Path.home() / ".rodoo" / "src"
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
