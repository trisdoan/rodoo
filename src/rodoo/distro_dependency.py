from abc import ABC, abstractmethod
import distro
from typing import List, Optional
from rodoo.output import Output
import subprocess


class DistroDependency(ABC):
    packages: List[str] = []

    @abstractmethod
    def get_packages(self) -> List[str]:
        pass

    @abstractmethod
    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        pass

    def install_dependencies(self, packages: List[str]):
        if not packages:
            return

        cmd = self._get_install_cmd(packages)
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            Output.error(f"Failed to execute command: {e}")


class Fedora(DistroDependency):
    packages = [
        "gcc",
        "createrepo",
        "libsass",
        "postgresql",
        "postgresql-contrib",
        "postgresql-devel",
        "postgresql-libs",
        "postgresql-server",
        "python3-devel",
        "rpmdevtools",
    ]

    def get_packages(self) -> List[str]:
        return self.packages

    def get_missing_installed_packages(self, packages: List[str]) -> List[str]:
        try:
            result = subprocess.run(
                ["dnf", "repoquery", "--installed", "--provides"],
                capture_output=True,
                text=True,
                check=True,
            )
            provides_result = result.stdout

            installed_provides = set()
            for line in provides_result.strip().split("\n"):
                provided_name = line.split(" ")[0]
                installed_provides.add(provided_name)

            not_installed = []
            for pkg in self.get_packages():
                if pkg not in installed_provides:
                    not_installed.append(pkg)
            return not_installed

        except (FileNotFoundError, subprocess.CalledProcessError):
            return []

    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        return ["sudo", "dnf", "install", "-y"] + packages


class Debian(DistroDependency):
    packages = [
        "gcc",
        "libsasl2-dev",
        "libldap2-dev",
        "libssl-dev",
        "libffi-dev",
        "libxml2-dev",
        "libxslt1-dev",
        "libjpeg-dev",
        "libpq-dev",
        "libsass-dev",
        "postgresql",
        "postgresql-client",
        "postgresql-contrib",
    ]

    def get_packages(self) -> List[str]:
        return self.packages

    def get_missing_installed_packages(self, packages: List[str]) -> List[str]:
        missing = []
        for pkg in self.get_packages():
            try:
                result = subprocess.run(
                    ["dpkg-query", "-W", "-f=${Status}", pkg],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if "install ok installed" not in result.stdout:
                    missing.append(pkg)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(pkg)
        return missing

    def install_dependencies(self, packages: List[str]):
        if not packages:
            return

        try:
            subprocess.run(
                ["sudo", "apt-get", "update"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            Output.error(f"Failed to run apt-get update: {e}")
            return
        except Exception as e:
            Output.error(f"An unexpected error occurred during apt-get update: {e}")
            return

        super().install_dependencies(packages)

    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        return ["sudo", "apt-get", "install", "-y"] + packages


class Arch(DistroDependency):
    packages = [
        "gcc",
        "postgresql",
        "postgresql-libs",
        "libxml2",
        "libxslt",
        "libjpeg",
        "libsass",
        "python",
    ]

    def get_packages(self) -> List[str]:
        return self.packages

    def get_missing_installed_packages(self, packages: List[str]) -> List[str]:
        not_installed = []
        for pkg in self.packages:
            result = subprocess.run(["pacman", "-Q", pkg], capture_output=True)
            if result.returncode != 0:
                not_installed.append(pkg)
        return not_installed

    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        return ["sudo", "pacman", "-S", "--noconfirm"] + packages


def get_distro() -> Optional[DistroDependency]:
    """Factory function to get the correct distro strategy."""
    distro_id = distro.id()
    if distro_id == "fedora":
        return Fedora()
    elif distro_id in ["ubuntu", "debian"]:
        return Debian()
    elif distro_id == "arch":
        return Arch()
    else:
        Output.warning(
            f"Automatic dependency installation for '{distro_id}' is not supported."
        )
        return None
