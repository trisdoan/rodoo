from pathlib import Path
from typing import List, Optional
import subprocess
import typer
from rodoo.runner import Runner
from rodoo.config import (
    ConfigFile,
    load_and_merge_profiles,
    create_profile,
    ODOO_URL,
    ENT_ODOO_URL,
)
import functools
from rodoo.utils.exceptions import UserError, SubprocessError
from rodoo.output import Output


def perform_update(versions_to_update: List[str], source_path: Path):
    repos = {
        "odoo": ODOO_URL,
        "enterprise": ENT_ODOO_URL,
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
                    run_subprocess(["git", "pull"], cwd=str(worktree_path), check=True)
                except SubprocessError as e:
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


def _parse_cli_params(args: dict) -> dict:
    cli_params = {}
    for arg, val in args.items():
        if val is not None:
            if arg == "module":
                cli_params["modules"] = [m.strip() for m in val.split(",")]
            elif arg != "profile":
                cli_params[arg] = val
    return cli_params


def _validate_required_cli_params(cli_params: dict):
    if "modules" not in cli_params or "version" not in cli_params:
        Output.error(
            "Module and version arguments are required when running without a profile or existing configuration."
        )
        raise typer.Exit(1)


def _handle_no_cli_params(profile: Optional[str]) -> dict:
    all_profiles, profile_sources = load_and_merge_profiles()
    config = {}

    if not all_profiles:
        if Output.confirm("No modules to run. Would you like to create a new profile?"):
            profile_name, new_profile, _ = create_profile()
            Output.success(f"Created profile '{profile_name}'.")
            return new_profile
        else:
            raise typer.Exit(1)

    profile_name_to_use = profile
    if not profile_name_to_use:
        if len(all_profiles) > 1:
            profiles_list = list(all_profiles.keys())
            profile_display = "\n".join(
                [f"[{i + 1}] {name}" for i, name in enumerate(profiles_list)]
            )
            prompt_message = f"Which profile to run:\n{profile_display}\n"
            choice = typer.prompt(prompt_message, default="", show_default=False)

            if choice.isdigit() and 1 <= int(choice) <= len(profiles_list):
                profile_name_to_use = profiles_list[int(choice) - 1]
            else:
                profile_name_to_use = choice
        elif len(all_profiles) == 1:
            profile_name_to_use = next(iter(all_profiles))

    if not profile_name_to_use:
        raise typer.Exit(1)

    if profile_name_to_use not in all_profiles:
        Output.error(f"Profile '{profile_name_to_use}' not found.")
        raise typer.Exit(1)

    config_path = profile_sources[profile_name_to_use]
    if Output.confirm(
        f"Run with profile '{profile_name_to_use}' from {config_path}?", default=True
    ):
        config = all_profiles[profile_name_to_use]
    else:
        raise typer.Exit(1)

    return config


def _handle_cli_params_present(profile: Optional[str], cli_params: dict) -> dict:
    all_profiles, profile_sources = load_and_merge_profiles()
    cwd = str(Path.cwd())

    profiles_in_cwd = {
        name: all_profiles[name]
        for name, path in profile_sources.items()
        if str(Path(path).parent) == cwd
    }

    if profiles_in_cwd:
        profile_to_update = None

        if profile:
            profile_to_update = profile
        elif len(profiles_in_cwd) == 1:
            profile_to_update = next(iter(profiles_in_cwd))
        elif len(profiles_in_cwd) > 1:
            profiles_list = list(profiles_in_cwd.keys())
            profile_display = "\n".join(
                [f"[{i + 1}] {name}" for i, name in enumerate(profiles_list)]
            )
            prompt_message = (
                f"Which profile to update:\n{profile_display}\n[leave blank for none]"
            )
            choice = typer.prompt(prompt_message, default="", show_default=False)

            if choice.isdigit() and 1 <= int(choice) <= len(profiles_list):
                profile_to_update = profiles_list[int(choice) - 1]
            else:
                profile_to_update = choice

        if profile_to_update and profile_to_update in profiles_in_cwd:
            if Output.confirm(
                f"Update profile '{profile_to_update}' with provided arguments?"
            ):
                config_path = profile_sources[profile_to_update]
                config_file = ConfigFile(config_path)
                profiles = config_file.configs.get("profile", {})
                profiles[profile_to_update].update(cli_params)
                config_file.update(profile_to_update, profiles[profile_to_update])
                Output.success(f"Profile '{profile_to_update}' updated.")

                # After updating, load the updated config for execution
                config = profiles[profile_to_update]
            else:
                # decline to update profile, run with CLI params directly
                _validate_required_cli_params(cli_params)
                config = cli_params
        else:
            # No profile to update or profile not found, run with CLI params directly
            _validate_required_cli_params(cli_params)
            config = cli_params
    else:
        # No config file found, run with CLI params directly
        _validate_required_cli_params(cli_params)
        config = cli_params

    return config


def process_cli_args(profile: Optional[str], args: dict) -> dict:
    cli_params = _parse_cli_params(args)

    # No CLI arguments provided (except possibly --profile)
    if not cli_params:
        config = _handle_no_cli_params(profile)
    else:
        config = _handle_cli_params_present(profile, cli_params)

    if not config.get("modules") or not config.get("version"):
        Output.error("No Odoo modules/version specified to run Odoo")
        raise typer.Exit(1)

    return config


def construct_runner(config: dict, cli_args: dict):
    runner_modules = config.get("modules")
    if runner_modules is None and cli_args.get("module") is not None:
        runner_modules = [m.strip() for m in cli_args["module"].split(",")]

    runner_kwargs = {
        "modules": runner_modules,
        "version": config.get("version", cli_args.get("version")),
        "python_version": config.get("python_version", cli_args.get("python_version")),
    }

    optional_params = {
        "force_install": config.get("force_install", cli_args.get("force_install")),
        "force_update": config.get("force_update", cli_args.get("force_update")),
        "db": config.get("db", cli_args.get("db")),
        "paths": config.get("paths"),
        "enterprise": config.get("enterprise"),
        "extra_params": config.get("extra_params"),
        "python_packages": config.get("python_packages"),
        "db_host": config.get("db_host"),
        "db_user": config.get("db_user"),
        "db_password": config.get("db_password"),
        "load": config.get("load"),
        "workers": config.get("workers"),
        "max_cron_threads": config.get("max_cron_threads"),
        "limit_time_cpu": config.get("limit_time_cpu"),
        "limit_time_real": config.get("limit_time_real"),
        "http_interface": config.get("http_interface"),
    }

    for key, value in optional_params.items():
        if value is not None:
            runner_kwargs[key] = value

    return Runner(**runner_kwargs)


def run_subprocess(
    command: List[str],
    check: bool = True,
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    A wrapper around subprocess.run with standardized error handling.
    Args:
        command: The command to execute.
        check: If True, raise SubprocessError on non-zero exit codes.
        **kwargs: Additional arguments to pass to subprocess.run.
    Returns:
        A subprocess.CompletedProcess instance.
    Raises:
        SubprocessError: If the command fails and check is True.
    """
    # Set text=True by default if not provided and output is captured
    if kwargs.get("capture_output") and "text" not in kwargs:
        kwargs["text"] = True

    try:
        return subprocess.run(
            command,
            check=check,
            **kwargs,
        )
    except subprocess.CalledProcessError as e:
        raise SubprocessError(
            message=f"Command '{' '.join(str(c) for c in command)}' failed.",
            command=command,
            exit_code=e.returncode,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
        ) from e
    except FileNotFoundError as e:
        raise SubprocessError(
            message=f"Command not found: {command[0]}",
            command=command,
            exit_code=127,
            stdout="",
            stderr=str(e),
        ) from e


def handle_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except UserError as e:
            if isinstance(e, SubprocessError):
                Output.error(f"A command failed to run: {e.args[0]}")
                Output.info(f"Command: {' '.join(str(c) for c in e.command)}")
                if e.stdout:
                    Output.info(f"Stdout: {e.stdout}")
                if e.stderr:
                    Output.error(f"Stderr: {e.stderr}")
            else:
                Output.error(str(e))
            raise typer.Exit(1)
        except Exception as e:
            Output.error(str(e))
            # TODO: for unexpected errors, log the full traceback for debugging
            raise typer.Exit(1)

    return wrapper
