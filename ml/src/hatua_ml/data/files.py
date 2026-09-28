"""Checks that raw data files exist before a loader tries to read them."""
from pathlib import Path


class DataFileNotFoundError(FileNotFoundError):
    """A raw survey file is missing from the expected location."""


def require_file(path, description: str) -> Path:
    """Return `path` as a Path, or raise a clear error if it does not exist."""
    path = Path(path)
    if not path.is_file():
        raise DataFileNotFoundError(
            f"{description} not found.\n"
            f"  Looked for: {path}\n"
            f"  Download it from the survey provider and place it there, "
            f"or set HATUA_DATA_DIR to the folder that contains raw/.\n"
            f"  Note: file names are case-sensitive on Linux and Colab."
        )
    return path