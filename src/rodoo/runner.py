from dataclasses import dataclass
from platformdirs import user_config_path
from pathlib import Path
from typing import Optional, List
import ast
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import subprocess
import shlex
import os
import time
import typer
import json

from .distro_dependency import get_distro
from .config import APP_NAME
from .exceptions import UserError
from .output import Output

ODOO_URL = "git@github.com:odoo/odoo.git"
ENT_ODOO_URL = "git@github.com:odoo/enterprise.git"
CONFIG_DIR = user_config_path(appname=APP_NAME, appauthor=False, ensure_exists=True)
BARE_REPO = CONFIG_DIR / "odoo.git"
ENT_BARE_REPO = CONFIG_DIR / "enterprise.git"


"""
Runner organizes Odoo source code and development environments in the following directory structure:

~/.config/rodoo/
├── odoo.git/                    # Bare repository for Odoo core
├── enterprise.git/              # Bare repository for Odoo Enterprise
└── {version}/                   # Version-specific directory
    ├── odoo/                    # Odoo core worktree (from odoo.git)
    └── enterprise/              # Odoo Enterprise worktree (from enterprise.git)
├── venvs/                       # Python virtual environments
│   └── odoo-{version}-py{python_version}/
├── pid/                         # active Odoo process 
│   └── 

"""


@dataclass
class Runner:
    modules: list[str]
    version: float
    python_version: str
    db: Optional[str] = None
    paths: Optional[List[Path]] = None
    enterprise: Optional[bool] = False
    force_install: Optional[bool] = False
    force_update: Optional[bool] = False
    extra_params: Optional[str] = None
    python_packages: Optional[List[str]] = None
    db_host: Optional[str] = "localhost"
    db_user: Optional[str] = "odoo"
    db_password: Optional[str] = "odoo"
    load: Optional[list[str]] = None
    workers: Optional[int] = 0
    max_cron_threads: Optional[int] = 0
    limit_time_cpu: Optional[int] = 3600
    limit_time_real: Optional[int] = 3600
    http_interface: Optional[str] = "localhost"

    def __post_init__(self) -> None:
        self.app_dir = CONFIG_DIR

        if not self.python_version:
            venvs_dir = self.app_dir / "venvs"
            if venvs_dir.exists():
                pattern = f"odoo-{self.version}-py*"
                existing_venvs = sorted(
                    [p.name for p in venvs_dir.glob(pattern)], reverse=True
                )
                if existing_venvs:
                    latest_venv = existing_venvs[0]
                    self.python_version = latest_venv.split("-py")[-1]
                    Output.info(
                        f"Found existing environment for Odoo {self.version}, using Python {self.python_version}."
                    )

        if self.paths:
            self.paths = [Path(p) for p in self.paths]

        self.odoo_root_dir = self.app_dir / str(self.version)
        self.odoo_root_dir.mkdir(parents=True, exist_ok=True)
        self.odoo_src_path = self.odoo_root_dir / "odoo"
        self.enterprise_src_path = self.odoo_root_dir / "enterprise"

        # pull code
        self._setup_odoo_source()
        if self.enterprise:
            self._setup_enterprise_source()

        self.modules_paths = self._get_module_paths()

        self._sanity_check()

        # python env setup
        self.venv = f"odoo-{self.version}-py{self.python_version}"
        self.venv_path = self.app_dir / "venvs" / self.venv

        #### setup dev env ###
        # assume dev was setup if
        # package odoo already exists
        if not self._is_env_ready():
            self._install_system_packages()
            self._setup_python_env()

        # python dependencies
        self._install_extra_python_packages()

        # setup db name
        if not self.db:
            version_major = int(self.version)
            module_name = "_".join(self.modules) if self.modules else "nan"
            self.db = f"v{version_major}_{module_name}"

        # prepare odoo cli arguments
        self.odoo_cli_params = self._prepare_odoo_cli_params()

    ### main API ###
    def run(self):
        self._foreground_run()

    def upgrade(self):
        pass

    def run_test(self):
        pass

    # TODO: implement detach mode
    def _background_run(self):
        cmd = [
            "uv",
            "run",
            "--python",
            self.python_version,
            "odoo",
        ] + self.odoo_cli_params

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(self.venv_path)

        try:
            process = subprocess.Popen(
                cmd,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Wait for a few seconds to see if it fails
            time.sleep(3)
            # Check if the process has already terminated
            poll_result = process.poll()
            if poll_result is not None:
                if poll_result != 0:
                    stdout, stderr = process.communicate()
                    raise UserError(
                        f"Odoo failed to start with exit code {poll_result}.\n--- STDERR ---\n{stderr}\n--- STDOUT ---\n{stdout}"
                    )
            else:
                # Assume success after 3s
                Output.success(
                    f"Odoo server started in the background with PID: {process.pid}"
                )
                Output.info("You can stop the server using the 'stop' command.")

        except FileNotFoundError:
            raise UserError(f"Command not found: {cmd[0]}")
        except Exception as e:
            raise UserError(f"Odoo failed to start. Details:\n{e}") from e

    def _foreground_run(self):
        cmd = [
            "uv",
            "run",
            "--python",
            self.python_version,
            "odoo",
        ] + self.odoo_cli_params

        process_env = os.environ.copy()
        process_env["VIRTUAL_ENV"] = str(self.venv_path)

        try:
            subprocess.run(cmd, env=process_env)
        except FileNotFoundError:
            raise UserError(f"Command not found: {cmd[0]}")
        except Exception as e:
            raise UserError(f"Odoo failed to start. Details:\n{e}") from e

    def _create_progress(self):
        return Progress(
            SpinnerColumn("dots"),
            TextColumn("[bold blue]{task.description}"),
            transient=True,
        )

    def _setup_odoo_source(self):
        if not self.odoo_src_path.exists():
            with self._create_progress() as progress:
                progress.add_task(description="Cloning Odoo source", total=None)
                self._ensure_bare_repo()
                self.odoo_src_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        str(self.odoo_src_path),
                        str(self.version),
                    ],
                    check=True,
                    cwd=BARE_REPO,
                    capture_output=True,
                )

    def _ensure_bare_repo(self):
        if not BARE_REPO.exists():
            BARE_REPO.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--bare", ODOO_URL, str(BARE_REPO)],
                check=True,
                capture_output=True,
            )

    def _ensure_enterprise_bare_repo(self):
        if not ENT_BARE_REPO.exists():
            ENT_BARE_REPO.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--bare", ENT_ODOO_URL, str(ENT_BARE_REPO)],
                check=True,
                capture_output=True,
            )

    def _setup_enterprise_source(self):
        if not self.enterprise_src_path.exists():
            with self._create_progress() as progress:
                progress.add_task(
                    description="Setting up Odoo Enterprise source", total=None
                )
                self._ensure_enterprise_bare_repo()
                self.enterprise_src_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        str(self.enterprise_src_path),
                        str(self.version),
                    ],
                    check=True,
                    cwd=ENT_BARE_REPO,
                    capture_output=True,
                )

    def _install_system_packages(self):
        distro = get_distro(odoo_src_path=self.odoo_src_path)
        if distro:
            need_to_install = distro.get_missing_installed_packages(distro.packages)
            if not need_to_install:
                return

            typer.echo("Installing system-level dependencies...")
            distro.install_dependencies(need_to_install)

    def _is_env_ready(self):
        if not self.venv_path.exists():
            return False

        # Check if odoo is installed in the venv
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(self.venv_path)
        result = subprocess.run(
            ["uv", "pip", "list", "--format", "json"],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False

        try:
            packages = json.loads(result.stdout)
            package_names = [pkg["name"] for pkg in packages]
            return "odoo" in package_names
        except (json.JSONDecodeError, KeyError):
            return False

    def _setup_python_env(self):
        # Check if python version is available
        result = subprocess.run(
            ["uv", "python", "find", self.python_version], capture_output=True
        )
        python_installed = result.returncode == 0

        if not python_installed:
            with self._create_progress() as progress:
                progress.add_task(
                    description="Setting up Python environment", total=None
                )
                subprocess.run(
                    ["uv", "python", "install", self.python_version],
                    check=True,
                    capture_output=True,
                )

        # assume that all packages installed successfully
        if self.venv_path.exists():
            return
        with self._create_progress() as progress:
            progress.add_task(
                description="Setting up Python virtual environment", total=None
            )
            # setup virtual env
            self.venv_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["uv", "venv", "--python", self.python_version, str(self.venv_path)],
                check=True,
                capture_output=True,
            )

            # install odoo as editable named package
            env = os.environ.copy()
            env["VIRTUAL_ENV"] = str(self.venv_path)

            subprocess.run(
                ["uv", "pip", "install", "-e", f"file://{self.odoo_src_path}#egg=odoo"],
                check=True,
                env=env,
                capture_output=True,
            )

            requirements_file = self.odoo_src_path / "requirements.txt"
            if requirements_file.exists():
                subprocess.run(
                    ["uv", "pip", "install", "-r", str(requirements_file)],
                    check=True,
                    env=env,
                    capture_output=True,
                )

    def _sanity_check(self):
        if not self.python_version:
            raise UserError(
                "Python version is required. Please specify it with --python-version option."
            )

        if not self.modules:
            raise UserError("No module passed")

        # ensure dependencies
        all_odoo_deps = set()
        missing_odoo_deps = set()
        self.python_deps = set()
        queue = list(self.modules)

        available_modules = {}
        for path_obj in self.modules_paths:
            if not path_obj.is_dir():
                continue
            for module_dir in path_obj.iterdir():
                if module_dir.is_dir() and (module_dir / "__manifest__.py").exists():
                    available_modules[module_dir.name] = module_dir / "__manifest__.py"

        while queue:
            module_name = queue.pop(0)
            if module_name in all_odoo_deps:
                continue
            if module_name not in available_modules:
                missing_odoo_deps.add(module_name)
                continue
            all_odoo_deps.add(module_name)
            manifest_path = available_modules[module_name]
            try:
                with open(manifest_path, "r") as f:
                    manifest_str = f.read()
                manifest = ast.literal_eval(manifest_str)
                if "python" in manifest and isinstance(manifest.get("python"), list):
                    for dep in manifest["python"]:
                        # Find need-to-install Py package
                        # to be installed in _install_extra_python_packages
                        self.python_deps.add(dep)
                if "depends" in manifest and isinstance(manifest.get("depends"), list):
                    for dep in manifest["depends"]:
                        if dep not in all_odoo_deps:
                            queue.append(dep)
            except Exception:
                pass

        if missing_odoo_deps:
            missing_requested = missing_odoo_deps.intersection(self.modules)
            missing_transitive = missing_odoo_deps - missing_requested
            error_msg = ""
            if missing_requested:
                error_msg += f"The following modules requested by you were not found: {', '.join(missing_requested)}. "
            if missing_transitive:
                error_msg += f"The following transitive dependencies were not found: {', '.join(missing_transitive)}."
            raise UserError(error_msg)

    # TODO: workaround to fix failed buid
    def _patch_odoo_requirements(self):
        requirements_file = self.odoo_root_dir / "odoo" / "requirements.txt"
        if not requirements_file.is_file():
            return

        if self.version == 16.0:
            content = requirements_file.read_text()

    def _get_module_paths(self):
        paths = []
        if (path := self.odoo_src_path / "addons").exists():
            paths.append(path)
        if (path := self.odoo_src_path / "odoo" / "addons").exists():
            paths.append(path)
        if self.enterprise:
            paths.append(self.enterprise_src_path)
        if self.paths:
            for path in self.paths:
                paths.append(path)
        return paths

    def _install_extra_python_packages(self):
        if self.python_packages or self.python_deps:
            with self._create_progress() as progress:
                progress.add_task(
                    description="Installing extra Python packages", total=None
                )
                packages = []
                if self.python_packages:
                    packages.extend(self.python_packages)
                if self.python_deps:
                    packages.extend(self.python_deps)

                if not packages:
                    return

                env = os.environ.copy()
                env["VIRTUAL_ENV"] = str(self.venv_path)

                subprocess.run(
                    ["uv", "pip", "install"] + packages,
                    check=True,
                    env=env,
                    capture_output=True,
                )

    def _prepare_odoo_cli_params(self):
        options = []

        options.extend(["-d", self.db])
        options.extend(["--addons-path", ",".join(str(p) for p in self.modules_paths)])

        if self.force_install:
            options.extend(["-i", ",".join(self.modules)])
        if self.force_update:
            options.extend(["-u", ",".join(self.modules)])

        if self.load:
            options.extend(["--load", ",".join(self.load)])

        if self.extra_params:
            options.extend(shlex.split(self.extra_params))

        managed_params = {
            "db_host": self.db_host,
            "db_user": self.db_user,
            "db_password": self.db_password,
            "workers": self.workers,
            "max-cron-threads": self.max_cron_threads,
            "limit-time-cpu": self.limit_time_cpu,
            "limit-time-real": self.limit_time_real,
            "http-interface": self.http_interface,
        }

        existing_flags = {opt.split("=")[0] for opt in options if opt.startswith("--")}

        for key, value in managed_params.items():
            cli_key = f"--{key}"
            if value and cli_key not in existing_flags:
                options.extend([cli_key, str(value)])

        # path to store server pid, used to identify active odoo process
        options.extend(
            [
                "--pidfile",
                "=",
            ]
        )

        return options
