from pathlib import Path
import typer
from typing import Optional
from rodoo.runner import Runner
from rodoo.output import Output
from rodoo.exceptions import UserError
from rodoo.config import (
    ConfigFile,
    load_and_merge_profiles,
    create_profile,
)

app = typer.Typer(pretty_exceptions_enable=False)

"""
Desired behaviors of cli
1. No profile, no args → look for config in cwd → if none, exit with help
2. Profile passed → load config → if missing, error
3. Profile + args → load config, prompt to update
4. If no --profile but config exists → prompt to update
5. Args only, no profile, no config → run directly
"""


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
            profile_name_to_use = typer.prompt(
                f"Which profile to run? ({', '.join(all_profiles.keys())})",
                default="",
                show_default=False,
            )
        elif len(all_profiles) == 1:
            profile_name_to_use = next(iter(all_profiles))

    if not profile_name_to_use:
        raise typer.Exit(1)

    if profile_name_to_use not in all_profiles:
        Output.error(f"Profile '{profile_name_to_use}' not found.")
        raise typer.Exit(1)

    config_path = profile_sources[profile_name_to_use]
    if Output.confirm(f"Run with profile '{profile_name_to_use}' from {config_path}?"):
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
            profile_to_update = typer.prompt(
                f"Which profile to update? ({', '.join(profiles_in_cwd.keys())}) [leave blank for none]",
                default="",
            )

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


def _construct_runner(config: dict, cli_args: dict) -> Runner:
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
    db: Optional[str] = typer.Option(None, help="Database name"),
):
    """Running Odoo instance"""
    args = {k: v for k, v in locals().items() if k != "profile" and v is not None}
    config = process_cli_args(profile, args)

    try:
        runner = _construct_runner(config, args)
        runner.run()
    except UserError as e:
        Output.error(str(e))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
