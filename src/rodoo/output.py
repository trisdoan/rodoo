import typer


class Output:
    @staticmethod
    def success(message: str):
        typer.secho(f"✔ {message}", fg=typer.colors.GREEN, bold=True)

    @staticmethod
    def info(message: str):
        typer.secho(f"ℹ {message}", fg=typer.colors.BLUE)

    @staticmethod
    def warning(message: str):
        typer.secho(f"⚠ {message}", fg=typer.colors.YELLOW)

    @staticmethod
    def error(message: str):
        typer.secho(f"✖ {message}", fg=typer.colors.RED, err=True)

    @staticmethod
    def confirm(message: str, default: bool = False) -> bool:
        return typer.confirm(message, default=default)
