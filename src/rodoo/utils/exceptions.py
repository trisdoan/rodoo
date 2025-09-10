class UserError(Exception):
    pass


class UserWarning(Exception):
    pass


class ConfigurationError(UserError):
    pass


class SubprocessError(UserError):
    def __init__(self, message, command, exit_code, stdout, stderr):
        super().__init__(message)
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        return f"""{super().__str__()}
  Command: {" ".join(str(c) for c in self.command)}
  Exit Code: {self.exit_code}
  Stdout: {self.stdout}
  Stderr: {self.stderr}"""


class EnvironmentError(UserError):
    """Exception for environment-related errors (e.g., missing dependencies)."""

    pass

