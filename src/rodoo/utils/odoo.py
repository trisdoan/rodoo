import shlex
from typing import Any, Dict, List


def _add_params(
    options: List[str], params: Dict[str, Any], replace_underscore: bool = True
):
    """
    Adds parameters to the options list, avoiding duplicates for --flags.
    """
    existing_flags = {opt.split("=")[0] for opt in options if opt.startswith("--")}
    for key, value in params.items():
        if replace_underscore:
            cli_key = f"--{key.replace('_', '-')}"
        else:
            cli_key = f"--{key}"

        if value and cli_key not in existing_flags:
            options.extend([cli_key, str(value)])


def _get_common_options(runner) -> List[str]:
    options: List[str] = []
    options.extend(["-d", runner.db])
    options.extend(["--addons-path", ",".join(str(p) for p in runner.modules_paths)])

    common_params = {
        "db_host": runner.db_host,
        "db_user": runner.db_user,
        "db_password": runner.db_password,
    }
    _add_params(options, common_params, replace_underscore=False)
    return options


def build_run_command(runner) -> List[str]:
    """
    Builds the command for running Odoo.
    """
    options = _get_common_options(runner)

    if runner.force_install:
        options.extend(["-i", ",".join(runner.modules)])
    if runner.force_update:
        options.extend(["-u", ",".join(runner.modules)])

    if runner.load:
        options.extend(["--load", ",".join(runner.load)])

    run_params = {
        "workers": runner.workers,
        "max_cron_threads": runner.max_cron_threads,
        "limit_time_cpu": runner.limit_time_cpu,
        "limit_time_real": runner.limit_time_real,
        "http_interface": runner.http_interface,
    }
    _add_params(options, run_params, replace_underscore=True)

    if runner.extra_params:
        options.extend(shlex.split(runner.extra_params))

    return options


def build_upgrade_command(runner) -> List[str]:
    """
    Builds the command for upgrading Odoo modules.
    """
    options = _get_common_options(runner)
    options.extend(["--stop-after-init"])
    options.extend(["-u", ",".join(runner.modules)])

    if runner.extra_params:
        options.extend(shlex.split(runner.extra_params))

    return options


def build_test_command(runner) -> List[str]:
    """
    Builds the command for running Odoo tests.
    """
    options = _get_common_options(runner)
    options.extend(["--test-enable"])
    options.extend(["--stop-after-init"])
    options.extend(["-i", ",".join(runner.modules)])
    options.extend(["-u", ",".join(runner.modules)])

    if runner.extra_params:
        options.extend(shlex.split(runner.extra_params))

    return options


def build_shell_command(runner) -> List[str]:
    """
    Builds the command for starting an Odoo shell.
    """
    options = _get_common_options(runner)
    options.extend(["--no-http"])

    if runner.extra_params:
        options.extend(shlex.split(runner.extra_params))

    return options


def build_translate_command(runner, modules, language, translation_file) -> List[str]:
    """
    Builds the command for exporting translations.
    """
    options: List[str] = []
    options.extend(["-d", runner.db])

    db_params = {
        "db_host": runner.db_host,
        "db_user": runner.db_user,
        "db_password": runner.db_password,
    }
    for key, value in db_params.items():
        cli_key = f"--{key}"
        options.extend([cli_key, str(value)])

    options.extend(["--stop-after-init"])
    options.extend(["--modules", modules])
    options.extend(["--i18n-export", str(translation_file)])
    options.extend(["--language", language])

    if runner.extra_params:
        options.extend(shlex.split(runner.extra_params))

    return options
