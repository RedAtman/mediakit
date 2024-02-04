import glob
import os
from typing import Any, Dict, Optional


def change_file_extension(
    folder: Optional[str] = None,
    old_ext: Optional[str] = None,
    new_ext: Optional[str] = None,
    **kwargs: Any,
):
    if not folder or not old_ext or not new_ext:
        raise ValueError("folder, old_ext, new_ext must be provided")
    # Create a case-insensitive glob pattern: samples/*.[mM][pP][44]
    old_ext_pattern = "".join([f"[{c.lower()}{c.upper()}]" for c in old_ext])
    pathname_pattern: str = os.path.join(folder, f"*.{old_ext_pattern}")
    result: Dict[str, Any] = {}
    for filename in glob.glob(pathname_pattern):
        base = os.path.splitext(filename)[0]
        os.rename(filename, base + f".{new_ext}")
        result[filename] = base + f".{new_ext}"
    return result
