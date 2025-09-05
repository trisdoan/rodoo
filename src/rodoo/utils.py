from pathlib import Path
from typing import List
import subprocess
from rodoo.output import Output


def perform_update(versions_to_update: List[str], source_path: Path):
    repos = {
        "odoo": "https://github.com/odoo/odoo.git",
        "enterprise": "https://github.com/odoo/enterprise.git",
    }

    # First, ensure the main 'odoo' and 'enterprise' repos are cloned and up-to-date.
    for repo_name, repo_url in repos.items():
        repo_path = source_path / repo_name
        if not repo_path.exists():
            Output.info(f"Cloning {repo_name} repository from {repo_url}...")
            subprocess.run(["git", "clone", repo_url, str(repo_path)], check=True)
        else:
            Output.info(f"Fetching updates for {repo_name} repository...")
            subprocess.run(["git", "fetch", "--prune"], cwd=str(repo_path), check=True)

    # update/create their worktrees.
    for version in versions_to_update:
        Output.info(f"Processing Odoo version {version}...")
        for repo_name in repos:
            repo_path = source_path / repo_name
            worktree_path = source_path / version / repo_name

            if worktree_path.exists():
                Output.info(f"  Updating {repo_name} worktree for version {version}...")
                try:
                    subprocess.run(["git", "pull"], cwd=str(worktree_path), check=True)
                except subprocess.CalledProcessError as e:
                    Output.error(
                        f"Failed to update {repo_name} for version {version}: {e}"
                    )
            else:
                Output.info(f"  Creating {repo_name} worktree for version {version}...")
                worktree_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    branch_exists_cmd = subprocess.run(
                        [
                            "git",
                            "show-ref",
                            "--verify",
                            f"refs/remotes/origin/{version}",
                        ],
                        cwd=str(repo_path),
                        capture_output=True,
                        text=True,
                    )
                    if branch_exists_cmd.returncode != 0:
                        Output.warning(
                            f"  Branch '{version}' does not exist in {repo_name} remote. Skipping."
                        )
                        continue

                    subprocess.run(
                        ["git", "worktree", "add", str(worktree_path), version],
                        cwd=str(repo_path),
                        check=True,
                    )
                except subprocess.CalledProcessError as e:
                    Output.error(
                        f"Failed to create worktree for {repo_name} version {version}: {e}"
                    )
