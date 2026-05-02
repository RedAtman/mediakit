import json
import mimetypes
import os
import re


__all__ = [
    "guess",
]

categories = [
    "video",
    "audio",
    "archive",
    "document",
    "software",
    "image",
    "other",
]

rar_part_re = re.compile(r"^\.r[0-9]+$")


def _load_extension_map():
    """Build a flat {extension: category} dict from media_types.json."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "media_types.json")) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    result = {}
    for category, extensions in data.items():
        for ext in extensions:
            result[ext] = category
    return result


_extension_map = _load_extension_map()


def guess(filename):
    """Guess the category of the file.

    Args:
        filename (str): The filename.

    Returns:
        str | None: The category of the file.
    """
    typ = None
    mime = mimetypes.guess_type(filename, strict=False)[0]
    if mime:
        typ = mime_to_category(mime)
    if typ is None:
        ext = os.path.splitext(filename)[1]
        if ext:
            typ = extension_to_category(ext)
    return typ


def extension_to_category(ext: str):
    ext = ext.lower()
    category = _extension_map.get(ext)
    if category is not None:
        return category
    if rar_part_re.match(ext):
        return "archive"
    return None


def mime_to_category(mime: str):
    typ, sub_typ = mime.split("/")
    sub_typ = sub_typ.lower()
    if typ == "video":
        return "video"
    elif typ == "audio":
        return "audio"
    elif typ == "image":
        return "image"
    elif typ in {"model", "message", "chemical"}:
        return "document"
    elif typ == "text":
        if sub_typ in {
            "vnd.dmclientscript",
            "x-c++hdr",
            "x-c++src",
            "x-chdr",
            "x-crontab",
            "x-csh",
            "x-csrc",
            "x-java",
            "x-makefile",
            "x-moc",
            "x-pascal",
            "x-pcs-gcd",
            "x-perl",
            "x-python",
            "x-sh",
            "x-tcl",
            "x-dsrc",
            "x-haskell",
            "x-literate-haskell",
        }:
            return "software"
        elif sub_typ in {"vnd.abc", "x-lilypond"}:
            return "audio"
        else:
            return "document"
    elif typ == "application":
        if sub_typ in {"dicom"}:
            return "image"
        elif sub_typ in {
            "ecmascript",
            "java-archive",
            "javascript",
            "java-vm",
            "vnd.android.package-archive",
            "x-debian-package",
            "x-msdos-program",
            "x-msi",
            "x-python-code",
            "x-redhat-package-manager",
            "x-ruby",
            "x-shockwave-flash",
            "x-silverlight",
            "x-cab",
            "x-sql",
        }:
            return "software"
        elif sub_typ in {
            "gzip",
            "rar",
            "x-7z-compressed",
            "x-apple-diskimage",
            "x-iso9660-image",
            "x-lha",
            "x-lzh",
            "x-gtar-compressed",
            "x-tar",
            "zip",
        }:
            return "archive"
        elif sub_typ in {
            "json",
            "msword",
            "oebps-package+xml",
            "onenote",
            "pdf",
            "postscript",
            "rtf",
            "smil+xml",
            "x-abiword",
            "x-hdf",
            "x-cbr",
            "x-cbz",
        }:
            return "document"
        elif any(
            sub_typ.startswith(t)
            for t in [
                "vnd.ms-",
                "vnd.oasis.opendocument",
                "vnd.openxmlformats-officedocument",
                "vnd.stardivision",
                "vnd.sun.xml",
            ]
        ):
            return "document"
        else:
            return None
    elif mime == "x-epoc/x-sisx-app":
        return "software"
    else:
        return None


if __name__ == "__main__":
    print(extension_to_category(".mp3"))
    print(extension_to_category(".rar"))
    print(extension_to_category(".txt"))
    print(extension_to_category(".pdf"))
    print(extension_to_category(".exe"))
    print(extension_to_category(".jpg"))
    print(extension_to_category(".mp4"))
    print(extension_to_category(".zip"))
    print(extension_to_category(".7z"))
    print(extension_to_category(".iso"))
    print(extension_to_category(".deb"))
    print(extension_to_category(".rpm"))
    print(extension_to_category(".tar"))
    print(extension_to_category(".gz"))
    print(extension_to_category(".bz2"))
