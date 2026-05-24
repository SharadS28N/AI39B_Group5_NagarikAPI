"""Minimal tempfile compatibility shim.

This workspace's Python installation is missing the standard library
`tempfile` module, so a small local replacement is provided to keep the
application and its dependencies working.
"""

from __future__ import annotations

import os
import shutil
import uuid
import random


__all__ = [
    "TemporaryFile",
    "NamedTemporaryFile",
    "TemporaryDirectory",
    "mkstemp",
    "mkdtemp",
    "gettempdir",
    "gettempdirb",
    "gettempprefix",
    "gettempprefixb",
    "tempdir",
    "template",
    "_RandomNameSequence",
]


template = "tmp"
tempdir = None


def gettempprefix() -> str:
    return template


def gettempdir() -> str:
    for env_name in ("TMPDIR", "TEMP", "TMP"):
        candidate = os.environ.get(env_name)
        if candidate:
            os.makedirs(candidate, exist_ok=True)
            return candidate

    fallback = os.path.join(os.getcwd(), "tmp")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def gettempdirb() -> bytes:
    return os.fsencode(gettempdir())


def gettempprefixb() -> bytes:
    return os.fsencode(template)


def _unique_name(prefix: str = template, suffix: str = "", dir: str | None = None) -> str:
    directory = dir or gettempdir()
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{prefix}{uuid.uuid4().hex}{suffix}")


class _RandomNameSequence:
    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"

    def __init__(self):
        self._random = random.Random()

    def __iter__(self):
        return self

    def __next__(self):
        return "".join(self._random.choice(self.characters) for _ in range(8))


def mkstemp(suffix: str = "", prefix: str = template, dir: str | None = None, text: bool = False):
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    while True:
        filename = _unique_name(prefix=prefix, suffix=suffix, dir=dir)
        try:
            fd = os.open(filename, flags, 0o600)
            return fd, filename
        except FileExistsError:
            continue


def mkdtemp(suffix: str = "", prefix: str = template, dir: str | None = None) -> str:
    while True:
        directory = _unique_name(prefix=prefix, suffix=suffix, dir=dir)
        try:
            os.mkdir(directory, 0o700)
            return directory
        except FileExistsError:
            continue


class _TemporaryFileWrapper:
    def __init__(self, file_obj, name: str, delete: bool):
        self._file = file_obj
        self.name = name
        self._delete = delete
        self._closed = False

    def __getattr__(self, item):
        return getattr(self._file, item)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def close(self):
        if self._closed:
            return
        try:
            self._file.close()
        finally:
            if self._delete:
                try:
                    os.unlink(self.name)
                except FileNotFoundError:
                    pass
            self._closed = True


def NamedTemporaryFile(
    mode: str = "w+b",
    buffering: int = -1,
    encoding: str | None = None,
    newline: str | None = None,
    suffix: str = "",
    prefix: str = template,
    dir: str | None = None,
    delete: bool = True,
):
    fd, filename = mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    file_obj = os.fdopen(fd, mode, buffering, encoding, newline)
    if delete:
        return _TemporaryFileWrapper(file_obj, filename, True)
    return _TemporaryFileWrapper(file_obj, filename, False)


def TemporaryFile(
    mode: str = "w+b",
    buffering: int = -1,
    encoding: str | None = None,
    newline: str | None = None,
    suffix: str = "",
    prefix: str = template,
    dir: str | None = None,
):
    return NamedTemporaryFile(
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        newline=newline,
        suffix=suffix,
        prefix=prefix,
        dir=dir,
        delete=True,
    )


class TemporaryDirectory:
    def __init__(self, suffix: str = "", prefix: str = template, dir: str | None = None):
        self.name = mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self._closed = False

    def __enter__(self):
        return self.name

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False

    def cleanup(self):
        if not self._closed:
            shutil.rmtree(self.name, ignore_errors=True)
            self._closed = True

    def __del__(self):
        self.cleanup()
