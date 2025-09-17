from pathlib import Path
from rodoo.output import Output
from typing import Optional, TypedDict, cast, List
import typer
from tomlkit.toml_file import TOMLFile
from tomlkit.toml_document import TOMLDocument
from tomlkit.exceptions import TOMLKitError
from platformdirs import user_config_path, user_data_path
import tomlkit


FILENAMES = [".rodoo.toml", "rodoo.toml"]
APP_NAME = "rodoo"

ODOO_URL = "git@github.com:odoo/odoo.git"
ENT_ODOO_URL = "git@github.com:odoo/enterprise.git"
CONFIG_DIR = user_config_path(appname=APP_NAME, appauthor=False, ensure_exists=True)
APP_HOME = user_data_path(appname=APP_NAME, appauthor=False, ensure_exists=True)
BARE_REPO = APP_HOME / "odoo.git"
ENT_BARE_REPO = APP_HOME / "enterprise.git"


class Profile(TypedDict, total=False):
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


class Config(TypedDict, total=False):
    profile: dict[str, Profile]


class ConfigFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.toml_file = TOMLFile(path)
        try:
            self.toml_doc = self.toml_file.read()
            self.configs: Config = cast(Config, self.toml_doc.unwrap())
        except OSError:
            self.toml_doc = TOMLDocument()
            self.configs = {}
        except TOMLKitError as e:
            Output.error(f"Invalid TOML configuration: {e}")

    def update(self, profile_name: str, new_config: Profile) -> None:
        """Update a specific profile in the configuration file."""
        if "profile" not in self.configs:
            self.configs["profile"] = {}
        self.configs["profile"][profile_name] = new_config
        self.write()

    def write(self) -> None:
        """
        Write in-memory config file at self.path
        """
        doc = tomlkit.document()
        profiles = self.configs.get("profile", {})
        profiles_to_write = {name: profile.copy() for name, profile in profiles.items()}

        for profile in profiles_to_write.values():
            if "paths" in profile and profile.get("paths"):
                profile["paths"] = [str(p) for p in profile["paths"]]

        doc.add("profile", profiles_to_write)
        self.toml_file.write(doc)


def search_cwd() -> Path | None:
    """Find config file in current working directory"""
    directory = Path.cwd()
    for f in FILENAMES:
        if (directory / f).exists():
            return directory / f
    return None


def search_config() -> Path | None:
    """Find config file in user’s default config directory"""
    try:
        directory = user_config_path(appname=APP_NAME, appauthor=False)
        if not directory.is_dir():
            return None

        for f in FILENAMES:
            config_path = directory / f
            if config_path.is_file():
                return config_path
    except Exception:
        return None

    return None


def load_config(config_path: Path | None) -> Config:
    config = _find_config_file(config_path)
    _sanity_check(config)
    return config


def _find_config_file(config_path: Path | None) -> Config:
    config: Config = {}
    found_file = None

    if config_path is not None and config_path.exists():
        found_file = config_path
    elif config_path is not None:
        Output.error(f"Configuration file not found: {config_path}")

    if found_file is None:
        for search in [search_cwd, search_config]:
            found_file = search()
            if found_file:
                break

    if found_file is not None:
        config_file = ConfigFile(found_file)
        config.update(config_file.configs)

        if "profile" in config:
            for profile_name, profile_config in config["profile"].items():
                if "paths" in profile_config and profile_config["paths"]:
                    resolved_paths = []
                    for p in profile_config["paths"]:
                        path = Path(p).expanduser()
                        if not path.is_absolute():
                            path = (found_file.parent / path).resolve()
                        resolved_paths.append(path)
                    profile_config["paths"] = resolved_paths

    return config


def find_all_config_paths() -> list[Path]:
    """
    Find all rodoo config files in precedence order:
    1. CWD/.rodoo.toml
    2. CWD/rodoo.toml
    3. USER/.rodoo.toml
    4. USER/rodoo.toml
    """
    paths = []
    # CWD
    for f in FILENAMES:
        p = Path.cwd() / f
        if p.exists():
            paths.append(p)
    # User config
    try:
        directory = user_config_path(appname=APP_NAME, appauthor=False)
        if directory.is_dir():
            for f in FILENAMES:
                p = directory / f
                if p.is_file():
                    paths.append(p)
    except Exception:
        pass
    return paths


def load_and_merge_profiles() -> tuple[dict[str, Profile], dict[str, Path]]:
    """
    Loads all profiles from all found config files and merges them.
    Returns a tuple of:
    - merged profiles dictionary
    - dictionary mapping profile names to their source file path.
    """
    config_paths = find_all_config_paths()
    merged_profiles: dict[str, Profile] = {}
    profile_sources: dict[str, Path] = {}

    # Iterate in reverse to load lower precedence files first
    for path in reversed(config_paths):
        config_file = ConfigFile(path)
        # handle case where config file is empty or invalid
        if not hasattr(config_file, "configs"):
            continue
        profiles = config_file.configs.get("profile", {})

        if profiles:
            # Resolve paths relative to the config file
            for profile_name, profile_config in profiles.items():
                if "paths" in profile_config and profile_config.get("paths"):
                    resolved_paths = []
                    for p in profile_config["paths"]:
                        path_obj = Path(p).expanduser()
                        if not path_obj.is_absolute():
                            path_obj = (path.parent / path_obj).resolve()
                        resolved_paths.append(path_obj)
                    profile_config["paths"] = resolved_paths

            merged_profiles.update(profiles)
            for name in profiles:
                profile_sources[name] = path

    _sanity_check({"profile": merged_profiles})
    return merged_profiles, profile_sources


def _sanity_check(config: Config) -> None:
    if not isinstance(config, dict):
        raise ConfigurationError("Configuration must be a dictionary")

    if "profile" in config:
        if not isinstance(config["profile"], dict):
            raise ConfigurationError("Profiles must be a dictionary")

        for profile_name, profile_config in config["profile"].items():
            if not isinstance(profile_config, dict):
                raise ConfigurationError(
                    f"Profile '{profile_name}' must be a dictionary"
                )

            # TODO: validate if odoo modules found in path
            if "modules" in profile_config:
                pass
            # Validate Odoo version
            if "version" in profile_config:
                version = profile_config["version"]
                if not isinstance(version, (int, float)):
                    raise ConfigurationError(
                        f"Version in profile '{profile_name}' must be a number"
                    )
            # TODO: a general check for other key in correct data types

    return


def create_profile() -> tuple[str, Profile, Path]:
    profile_name = typer.prompt("Enter a profile name", default="default")
    modules_str = typer.prompt("Enter comma-separated module names")
    version_str = typer.prompt("Enter Odoo version")

    new_profile: Profile = {
        "modules": [a.strip() for a in modules_str.split(",")],
        "version": float(version_str),
    }

    python_version = typer.prompt("Enter Python version", default="3.12")
    if python_version:
        new_profile["python_version"] = python_version

    db_name = typer.prompt(
        "Enter database name", default=f"{version_str}_{modules_str}"
    )
    if db_name:
        new_profile["db"] = db_name

    paths_str = typer.prompt("Enter comma-separated paths for modules", default="")
    if paths_str:
        new_profile["paths"] = [Path(p.strip()) for p in paths_str.split(",")]

    new_profile["enterprise"] = typer.confirm(
        "Is this an enterprise version?", default=False
    )

    new_profile["force_install"] = typer.confirm(
        "Force install modules?", default=False
    )

    new_profile["force_update"] = typer.confirm("Force update modules?", default=False)

    extra_params = typer.prompt("Enter extra parameters for Odoo", default="")
    if extra_params:
        new_profile["extra_params"] = extra_params

    python_packages_str = typer.prompt(
        "Enter comma-separated python packages",
        default="",
    )
    if python_packages_str:
        new_profile["python_packages"] = [
            p.strip() for p in python_packages_str.split(",")
        ]

    save_in_cwd = typer.confirm(
        "Save configuration in the current directory?", default=False
    )

    if save_in_cwd:
        config_path = Path.cwd() / "rodoo.toml"
    else:
        config_dir = user_config_path(appname=APP_NAME, appauthor=False, ensure_exists=True)
        config_path = config_dir / "rodoo.toml"

    config_file = ConfigFile(config_path)
    config_file.update(profile_name, new_profile)
    return profile_name, new_profile, config_path
