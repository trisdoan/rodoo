import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def in_virtual_env(venv_path: Path):
    original_virtual_env = os.environ.get("VIRTUAL_ENV")
    os.environ["VIRTUAL_ENV"] = str(venv_path)
    try:
        yield
    finally:
        if original_virtual_env:
            os.environ["VIRTUAL_ENV"] = original_virtual_env
        else:
            if "VIRTUAL_ENV" in os.environ:
                del os.environ["VIRTUAL_ENV"]
