from __future__ import annotations
import pytest
from gitmatch import chomp, pathway, trim_trailing_spaces


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
