from __future__ import annotations
import os
from pathlib import PureWindowsPath
import pytest
from gitmatch import chomp, is_complex_path, pathway, trim_trailing_spaces

ON_WINDOWS = os.name == "nt"


@pytest.mark.parametrize(
    "long,trimmed",
    [
        ("foo", "foo"),
        ("foo ", "foo"),
        ("foo  ", "foo"),
        ("foo\t", "foo"),
        (r"foo\ ", r"foo\ "),
        ("foo\\\t", "foo\\\t"),
        (r"foo\  ", r"foo\ "),
        (r"foo\\ ", r"foo\\"),
        (r"foo\\\ ", r"foo\\\ "),
        (r"foo \ ", r"foo \ "),
        (r"foo \  ", r"foo \ "),
        (r"foo \ \ ", r"foo \ \ "),
        (r"foo \ \  ", r"foo \ \ "),
    ],
)
def test_trim_trailing_spaces(long: str, trimmed: str) -> None:
    assert trim_trailing_spaces(long) == trimmed


@pytest.mark.parametrize(
    "path,ways",
    [
        ("foo", ["foo"]),
        ("foo/bar", ["foo", "foo/bar"]),
        ("foo/bar/baz/quux", ["foo", "foo/bar", "foo/bar/baz", "foo/bar/baz/quux"]),
    ],
)
def test_pathway(path: str, ways: list[str]) -> None:
    assert pathway(path) == ways


@pytest.mark.parametrize(
    "s,chomped",
    [
        ("", ""),
        ("\n", ""),
        ("\r", ""),
        ("\r\n", ""),
        ("foobar", "foobar"),
        ("foobar\n", "foobar"),
        ("foobar\r\n", "foobar"),
        ("foobar\r", "foobar"),
        ("foobar\n\r", "foobar\n"),
        ("foobar\n\n", "foobar\n"),
        ("foobar\nbaz", "foobar\nbaz"),
    ],
)
def test_chomp(s: str, chomped: str) -> None:
    assert chomp(s) == chomped
    assert chomp(s.encode("us-ascii")) == chomped.encode("us-ascii")


@pytest.mark.parametrize(
    "path,r",
    [
        ("foo", False),
        ("foo/bar", False),
        ("foo/bar/", False),
        ("/foo", True),
        ("/foo/bar", True),
        ("/foo/bar/", True),
    ],
)
def test_is_complex_path(path: str, r: bool) -> None:
    assert is_complex_path(path) == r


@pytest.mark.parametrize(
    "path",
    [
        "\\\\?\\C:\\",
        r"C:\foo\bar",
        r"\foo\bar",
        r"C:foo\bar",
        r"\\?\pictures\kittens",
        r"\\server\share",
        r"\\.\BrainInterface",
        r"\\?\UNC\server\share",
    ],
)
def test_is_complex_path_windows_nonsense(path: str) -> None:
    if ON_WINDOWS:
        assert is_complex_path(path)
    else:
        assert not is_complex_path(path)
    assert is_complex_path(PureWindowsPath(path))
