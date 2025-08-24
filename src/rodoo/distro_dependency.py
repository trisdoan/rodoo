from abc import ABC, abstractmethod
import distro
from typing import List, Optional
from pathlib import Path
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
        "createrepo",
        "libsass",
        "postgresql",
        "postgresql-contrib",
        "postgresql-devel",
        "postgresql-libs",
        "postgresql-server",
        "python3-PyPDF2",
        "python3-asn1crypto",
        "python3-babel",
        "python3-cbor2",
        "python3-chardet",
        "python3-cryptography",
        "python3-dateutil",
        "python3-decorator",
        "python3-devel",
        "python3-docutils",
        "python3-freezegun",
        "python3-geoip2",
        "python3-gevent",
        "python3-greenlet",
        "python3-idna",
        "python3-jinja2",
        "python3-libsass",
        "python3-lxml",
        "python3-markupsafe",
        "python3-mock",
        "python3-num2words",
        "python3-ofxparse",
        "python3-openpyxl",
        "python3-passlib",
        "python3-pillow",
        "python3-polib",
        "python3-psutil",
        "python3-psycopg2",
        "python3-ldap",
        "python3-pyOpenSSL",
        "python3-pyserial",
        "python3-pytz",
        "python3-pyusb",
        "python3-qrcode",
        "python3-reportlab",
        "python3-requests",
        "python3-rjsmin",
        "python3-six",
        "python3-stdnum",
        "python3-vobject",
        "python3-werkzeug",
        "python3-wheel",
        "python3-xlrd",
        "python3-xlsxwriter",
        "python3-xlwt",
        "python3-zeep",
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
    packages = []

    def __init__(self, odoo_src_path: Optional[Path] = None):
        self.odoo_src_path = odoo_src_path

    def get_packages(self) -> List[str]:
        if not self.odoo_src_path:
            Output.warning(
                "Odoo source path not available for Debian dependency check."
            )
            return []

        control_file = self.odoo_src_path / "debian" / "control"
        if not control_file.exists():
            Output.warning(f"Debian control file not found at {control_file}")
            return []

        content = control_file.read_text()
        return self._parse_dependencies(content)

    def _parse_dependencies(self, content: str) -> List[str]:
        all_deps = []
        in_deps = False
        relevant_sections = ["Depends:", "Recommends:"]

        for line in content.splitlines():
            is_new_section = False
            for section in relevant_sections:
                if line.startswith(section):
                    in_deps = True
                    is_new_section = True
                    line = line.split(":", 1)[1]
                    break

            if not is_new_section:
                stripped_line = line.strip()
                if not (stripped_line and stripped_line.startswith("#")) and not (
                    line and line[0].isspace()
                ):
                    in_deps = False

            if in_deps:
                line = line.split("#")[0].strip()
                if not line:
                    continue

                deps = [
                    p.strip()
                    for p in line.split(",")
                    if p and not p.strip().startswith("${")
                ]
                for dep in deps:
                    # take first alternative
                    pkg = dep.split("|")[0].strip()
                    # remove version spec
                    pkg = pkg.split(" ")[0].strip()
                    if pkg:
                        all_deps.append(pkg)
        return list(set(all_deps))

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
            Output.error(f"Failed to run apt-get update: {e.stderr.decode()}")
            return
        except Exception as e:
            Output.error(f"An unexpected error occurred during apt-get update: {e}")
            return

        super().install_dependencies(packages)

    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        return ["sudo", "apt-get", "install", "-y"] + packages


class Arch(DistroDependency):
    packages = [
        "shadow",
        "lsb-release",
        "postgresql",
        "python-asn1crypto",
        "python-babel",
        "python-cbor2",
        "python-chardet",
        "python-cryptography",
        "python-dateutil",
        "python-decorator",
        "python-docutils",
        "python-freezegun",
        "python-geoip2",
        "python-gevent",
        "python-greenlet",
        "python-idna",
        "python-pillow",
        "python-jinja",
        "python-libsass",
        "python-lxml",
        "python-markupsafe",
        "python-openpyxl",
        "python-passlib",
        "python-polib",
        "python-psutil",
        "python-psycopg2",
        "python-pyopenssl",
        "python-pytest",  # required by python-ofxparse
        "python-rjsmin",
        "python-qrcode",
        "python-reportlab",
        "python-requests",
        "python-pytz",
        "python-urllib3",
        "python-vobject",
        "python-werkzeug",
        "python-xlsxwriter",
        "python-xlrd",
        "python-zeep",
    ]
    aur_packages = [
        "python-num2words",
        "python-ofxparse",
        "python-pypdf2",
        "python-stdnum",
    ]

    def get_packages(self) -> List[str]:
        return self.packages + self.aur_packages

    def get_missing_installed_packages(self, packages: List[str]) -> List[str]:
        not_installed = []
        for pkg in self.packages:
            result = subprocess.run(["pacman", "-Q", pkg], capture_output=True)
            if result.returncode != 0:
                not_installed.append(pkg)

        try:
            subprocess.run(["yay", "-V"], check=True, capture_output=True)
            for pkg in self.aur_packages:
                result = subprocess.run(["yay", "-Q", pkg], capture_output=True)
                if result.returncode != 0:
                    not_installed.append(pkg)
        except (FileNotFoundError, subprocess.CalledProcessError):
            # yay not available, assume AUR packages are missing
            not_installed.extend(self.aur_packages)

        return not_installed

    def install_dependencies(self, packages: List[str]):
        pacman_pkgs = [pkg for pkg in packages if pkg in self.packages]
        aur_pkgs = [pkg for pkg in packages if pkg in self.aur_packages]

        if pacman_pkgs:
            cmd = ["sudo", "pacman", "-S", "--noconfirm"] + pacman_pkgs
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                Output.error(f"Failed to execute command: {e}")

        if aur_pkgs:
            cmd = ["yay", "-S", "--noconfirm"] + aur_pkgs
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                Output.error(f"Failed to execute command: {e}")

    def _get_install_cmd(self, packages: List[str]) -> List[str]:
        return []


def get_distro(odoo_src_path: Optional[Path] = None) -> Optional[DistroDependency]:
    """Factory function to get the correct distro strategy."""
    distro_id = distro.id()
    if distro_id == "fedora":
        return Fedora()
    elif distro_id in ["ubuntu", "debian"]:
        # pass odoo_src_path to trigger Odoo install script
        return Debian(odoo_src_path)
    elif distro_id == "arch":
        return Arch()
    else:
        Output.warning(
            f"Automatic dependency installation for '{distro_id}' is not supported."
        )
        return None
