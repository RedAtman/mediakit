import glob
import os
import shutil
from typing import Any, Dict, Optional


__all__ = [
    "change_file_extension",
    "soft_remove",
]


def change_file_extension(
    folder: Optional[str] = None,
    old_ext: Optional[str] = None,
    ext: Optional[str] = None,
    **kwargs: Any,
):
    if not folder or not old_ext or not ext:
        raise ValueError("folder, old_ext, ext must be provided")
    # Create a case-insensitive glob pattern: samples/*.[mM][pP][44]
    old_ext_pattern = "".join([f"[{c.lower()}{c.upper()}]" for c in old_ext])
    pathname_pattern: str = os.path.join(folder, f"*.{old_ext_pattern}")
    result: Dict[str, Any] = {}
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
