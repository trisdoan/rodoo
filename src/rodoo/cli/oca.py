import typer
from typing import Optional, List

from typing_extensions import Annotated

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def update(
    repos: Annotated[
        str,
        typer.Argument(
            help="Comma-separated list of repo names to update. E.g. 'web,social'"
        ),
    ],
    versions: Annotated[
        str,
        typer.Argument(
            help="Comma-separated list of Odoo versions to update. E.g. '16.0,17.0'"
        ),
    ],
):
    """Clone/Fetch OCA addons repositories."""
    repo_list = [r.strip() for r in repos.split(",")]
    version_list = [v.strip() for v in versions.split(",")]
    typer.echo(f"Updating repos: {repo_list} for versions: {version_list}")


if __name__ == "__main__":
    app()
