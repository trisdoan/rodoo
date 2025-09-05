"""
OCA repos are organized in the following directory structure:

~/.config/rodoo/
├── oca/
    ├── oca-repo.git/
├── odoo.git/                    # Bare repository for Odoo core
├── enterprise.git/              # Bare repository for Odoo Enterprise
└── {version}/                   # Version-specific directory
    ├── odoo/                    # Odoo core worktree (from odoo.git)
    └── enterprise/              # Odoo Enterprise worktree (from enterprise.git)
    └── oca-repo/                     # OCA repo worktree (from oca/oca-repo.git)
├── venvs/                       # Python virtual environments
│   └── odoo-{version}-py{python_version}/
├── pid/                         # active Odoo process
│   └──

"""

import subprocess
from pathlib import Path

import typer
from typing_extensions import Annotated

from rodoo.output import Output


app = typer.Typer(pretty_exceptions_enable=False)


# FIXME: improve code
# FIXME: update Runner to take oca path into account when loading path


# FIXME: how about fetch new update?
def _update_repo(repo_name: str, version: str, config_path: Path):
    oca_base_path = config_path / "oca"
    bare_repo_path = oca_base_path / f"{repo_name}.git"
    repo_url = f"git@github.com:OCA/{repo_name}.git"

    if not bare_repo_path.exists():
        Output.info(f"Cloning bare repository for {repo_name}...")
        subprocess.run(
            ["git", "clone", "--bare", repo_url, str(bare_repo_path)],
            check=True,
            capture_output=True,
        )

    # FIXME: Check if the version branch does not exists
    # branch_check = subprocess.run(
    #     ["git", "show-ref", "--verify", f"refs/remotes/origin/{version}"],
    #     cwd=bare_repo_path,
    #     capture_output=True,
    #     text=True,
    # )
    # if branch_check.returncode != 0:
    #     Output.warning(
    #         f"Branch '{version}' not found for repo {repo_name}. Skipping."
    #     )
    #     return

    version_path = config_path / version
    version_path.mkdir(exist_ok=True, parents=True)
    worktree_path = version_path / repo_name

    if not worktree_path.exists():
        Output.info(f"Creating worktree for {repo_name} at version {version}...")
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                str(worktree_path),
                str(version),
            ],
            check=True,
            cwd=bare_repo_path,
            capture_output=True,
        )


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

    config_path = Path.home() / ".config" / "rodoo"
    oca_base_path = config_path / "oca"
    oca_base_path.mkdir(parents=True, exist_ok=True)

    Output.info(
        f"Updating repos: {', '.join(repo_list)} for versions: {', '.join(version_list)}"
    )

    for repo in repo_list:
        for version in version_list:
            _update_repo(repo, version, config_path)

    Output.success("Finished updating OCA repositories.")


if __name__ == "__main__":
    app()
