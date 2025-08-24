# Rodoo - Run Odoo

A CLI tool to streamline Odoo development environments.

> **Warning**
> This tool is designed purely for **Odoo development** purposes. It is not recommended for use in production environments.

## Installation

Before installing `rodoo`, you need to have `uv` installed on your system.

You can install `rodoo` using uv-tool:

```bash
uv tool install git+https://github.com/trisdoan/rodoo.git
```

## Features

-   **Automated Odoo Development Setup**: Clones the correct Odoo version from the official repository. Automatically creates and manages Python virtual environments for your projects using `uv`.
-   **Flexible Configuration**: Configure your Odoo instances via CLI arguments or through `rodoo.toml` configuration files.
-   **Profile Management**: Create and manage multiple configuration profiles for different projects.

## How It Works

`rodoo` is designed to be non-intrusive to your project's directory. It manages all the heavy components in a central location (`~/.config/rodoo` on Linux).

-   **Source Code**: Odoo source code (both Community and Enterprise) is cloned into version-specific subdirectories within the `rodoo` config folder. This means you only have one copy of each Odoo version on your system, which is then shared across projects.
-   **Virtual Environments**: Python virtual environments are managed by `uv` and are stored in a `venvs` subdirectory, keeping your projects clean from bulky `venv` folders.
-   **Profiles**: The core concept is the "profile". A profile is a collection of settings for a specific Odoo instance (e.g., modules, version, custom paths) defined in a `rodoo.toml` file. You can have multiple profiles for different projects. This file can be checked into your version control, making it easy to share project configurations with your team and ensure consistent environments across different machines.

## Quick Start

There are a few ways to use `rodoo`.

### 1. Direct CLI Arguments

You can start an Odoo instance by providing the module and version directly on the command line. `rodoo` will handle the rest.

```bash
rodoo start --module web --version 17.0 --python-version 3.11
```

### 2. Using a Configuration File

For more complex projects, you can create a `rodoo.toml` file in your project directory.

Here is an example `rodoo.toml`:

```toml
[profile.my_project]
modules = ["web", "crm", "sale"]
version = 17.0
python_version = "3.11"
enterprise = true
paths = ["./custom_addons"]
```

Then, you can start the instance using the profile name:

```bash
rodoo start --profile my_project
```

If you only have one profile, you can just run `rodoo start` and it will be selected automatically.

### 3. Interactive Profile Creation

If you run `rodoo start` in a directory with no configuration, it will prompt you to create a new profile interactively.
