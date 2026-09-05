"""Bounded, unambiguous JSON at untrusted/file boundaries. No product side effects."""
from __future__ import annotations
import json
import math
import os
import stat
from pathlib import Path


def strict_json(raw: bytes | str, *, max_bytes: int = 512_000, max_depth: int = 48):
    if isinstance(raw, bytes):
        if len(raw) > max_bytes:
            raise ValueError("JSON exceeds size limit")
        text = raw.decode("utf-8", errors="strict")
    elif isinstance(raw, str):
        if len(raw.encode("utf-8", errors="strict")) > max_bytes:
            raise ValueError("JSON exceeds size limit")
        text = raw
    else:
        raise ValueError("JSON input must be bytes or text")

    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out

    def no_constant(_):
        raise ValueError("non-finite JSON number")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=no_constant)
    except (RecursionError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON") from exc
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if depth > max_depth or nodes > 100_000:
            raise ValueError("JSON nesting/node limit")
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError("non-finite JSON number")
        if isinstance(item, str):
            item.encode("utf-8", errors="strict")  # reject unpaired surrogate escapes
        if isinstance(item, dict):
            for key, child in item.items():
                key.encode("utf-8", errors="strict")
                pending.append((child, depth + 1))
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def read_json_file(path: Path, *, max_bytes: int, private: bool = False):
    """Read one regular non-symlink leaf by fd; no stat/read-size race.

    Parent directories remain operator-controlled deployment inputs. This is not
    a sandbox against an administrator replacing the entire directory tree.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if path.is_symlink():
        raise ValueError("JSON file must not be a symlink")
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise ValueError("invalid JSON file")
        if os.name == "posix" and info.st_mode & (0o077 if private else 0o022):
            raise ValueError("unsafe JSON file permissions")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(max_bytes + 1)
        return strict_json(raw, max_bytes=max_bytes), raw
    finally:
        os.close(fd)
