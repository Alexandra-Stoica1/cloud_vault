def format_size(size_bytes: int) -> str:
    """Human-readable size, e.g. 1536 -> '2 KB'."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} TB"
