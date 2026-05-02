import glob
import hashlib
import os
import shutil
from typing import Any


__all__ = [
    "calculate_md5",
    "change_file_extension",
    "soft_remove",
]


def calculate_md5(file_path: str) -> str:
    """Calculate the MD5 sum of a file."""
    with open(file_path, "rb") as file:
        data = file.read()
        md5: str = hashlib.md5(data).hexdigest()
    return md5


def change_file_extension(
    folder: str | None = None,
    old_ext: str | None = None,
    ext: str | None = None,
    **kwargs: Any,
):
    if not folder or not old_ext or not ext:
        raise ValueError("folder, old_ext, ext must be provided")
    # Create a case-insensitive glob pattern: samples/*.[mM][pP][44]
    old_ext_pattern = "".join([f"[{c.lower()}{c.upper()}]" for c in old_ext])
    pathname_pattern: str = os.path.join(folder, f"*.{old_ext_pattern}")
    result: dict[str, Any] = {}
    for filename in glob.glob(pathname_pattern):
        base = os.path.splitext(filename)[0]
        os.rename(filename, base + f".{ext}")
        result[filename] = base + f".{ext}"
    return result


def soft_remove(file_path: str) -> None:
    basedir, filename = os.path.split(file_path)
    remove_folder = os.path.join(basedir, ".removed")
    if not os.path.exists(remove_folder):
        os.makedirs(remove_folder)
    shutil.move(file_path, os.path.join(remove_folder, filename))


if __name__ == "__main__":
    # change_file_extension(folder="samples", old_ext="mp4", ext="avi")
    # soft_remove("samples/zh.mp4")
    print(calculate_md5("README.md"))
