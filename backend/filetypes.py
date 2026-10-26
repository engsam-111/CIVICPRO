SAFE_TYPES = {
    "jpg": ("image/jpeg", [b"\xff\xd8\xff"]), "jpeg": ("image/jpeg", [b"\xff\xd8\xff"]), "png": ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    "gif": ("image/gif", [b"GIF87a", b"GIF89a"]), "webp": ("image/webp", []), "heic": ("image/heic", []), "heif": ("image/heif", []),
    "pdf": ("application/pdf", [b"%PDF-"]),
    "doc": ("application/msword", [b"\xd0\xcf\x11\xe0"]), "xls": ("application/vnd.ms-excel", [b"\xd0\xcf\x11\xe0"]),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [b"PK\x03\x04"]),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", [b"PK\x03\x04"]),
    "dwg": ("application/acad", [b"AC10"]), "csv": ("text/csv", None), "txt": ("text/plain", None),
}
INLINE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}


def safe_type(ext: str, data: bytes):
    """Returns a server-chosen content type when extension and file bytes agree, else None."""
    if ext not in SAFE_TYPES:
        return None
    ctype, magic = SAFE_TYPES[ext]
    if ext == "webp":
        ok = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif ext in ("heic", "heif"):
        ok = data[4:8] == b"ftyp"
    elif magic is None:
        try:
            text = data[:4096].decode("utf-8").lower()
        except UnicodeDecodeError:
            return None
        ok = "\x00" not in text and not any(t in text for t in ("<html", "<script", "<svg", "<!doctype"))
    else:
        ok = any(data.startswith(m) for m in magic)
    return ctype if ok else None
