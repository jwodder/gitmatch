from __future__ import annotations
import os
import os.path
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import shutil
import subprocess
from linesep import join_terminated, split_terminated
import pytest
import gitmatch

ON_WINDOWS = os.name == "nt"
ON_PYPY = platform.python_implementation() == "PyPy"

# Patterns, path, ignorecase, matched
CASES = [
    # Literal:
    (["foo"], "foo", False, True),
    (["foo"], "fo", False, False),
    (["foo"], "fooo", False, False),
    (["foo"], "ofoo", False, False),
    (["foo"], "bar", False, False),
    (["foo"], "bar/foo", False, True),
    (["foo"], "bar/baz/foo", False, True),
    (["foo"], "bar/foo/baz", False, True),
    (["foo"], "foo/bar", False, True),
    (["foo"], "foo/bar/baz", False, True),
    (["foo"], "FOO", False, False),
    (["foo"], "FOO", True, True),
    ([r"foo\\bar"], "foo/bar", False, False),
    # Trailing slash:
    (["foo/"], "foo", False, False),
    (["foo/"], "foo/", False, True),
    (["foo/"], "foo/quux", False, True),
    (["foo/"], "bar/foo", False, False),
    (["foo/"], "bar/foo/", False, True),
    (["foo/"], "bar/foo/quux", False, True),
    (["foo//"], "foo", False, False),
    (["foo//"], "foo/", False, False),
    (["foo//"], "foo/bar", False, False),
    (["foo//"], "foo/bar/", False, False),
    (["foo///"], "foo/", False, False),
    (["foo////"], "foo/", False, False),
    # Leading & internal slash:
    (["/foo"], "foo", False, True),
    (["/foo"], "bar/foo", False, False),
    (["foo/bar"], "foo/bar", False, True),
    (["foo/bar"], "foo/bar/quux", False, True),
    (["foo/bar"], "quux/foo/bar", False, False),
    (["foo/bar"], "quux/foo/bar/quux", False, False),
    # Question mark:
    (["f?o"], "foo", False, True),
    (["f?o"], "f/o", False, False),
    (["??"], "foo", False, False),
    (["???"], "foo", False, True),
    # Single asterisk:
    (["f*o"], "foo", False, True),
    (["f*o"], "fo", False, True),
    (["f*o"], "fglarcho", False, True),
    (["f*o"], "f/o", False, False),
    (["f*o"], "føo", False, True),
    (["f/*o"], "f/o", False, True),
    (["f/*o"], "f/glarch/o", False, False),
    (["*"], "foo", False, True),
    (["f*"], "foo", False, True),
    (["*f"], "foo", False, False),
    (["*o"], "foo", False, True),
    (["o*"], "foo", False, False),
    (["*foo*"], "foo", False, True),
    (["foo*"], "foo", False, True),
    (["*foo"], "foo", False, True),
    (["*oo"], ".foo", False, True),
    (["*foo"], ".foo", False, True),
    ([".*"], ".foo", False, True),
    (["*ob*a*r*"], "foobar", False, True),
    (["foo*bar"], "foo/quux/bar", False, False),
    (["*/foo"], "bar/foo", False, True),
    (["*/foo"], "quux/bar/foo", False, False),
    (["*/*/*"], "foo", False, False),
    (["*/*/*"], "foo/bar", False, False),
    (["foo/*"], "foo/", False, False),
    (["foo/*"], "foo/bar", False, True),
    (["*/bar*"], "foo/bar", False, True),
    (["*/bar*"], "foo/bar/baz", False, True),
    # Double asterisk:
    (["foo**"], "foo", False, True),
    (["foo**"], "foo/bar/baz", False, True),
    (["foo**bar"], "foobar", False, True),
    (["foo**bar"], "fooquuxbar", False, True),
    (["foo**bar"], "foo/bar", False, False),
    (["foo**bar"], "foo/quux/bar", False, False),
    (["foo/**"], "foo", False, False),
    (["foo/**"], "foo/", False, False),
    (["foo/**"], "foo/bar", False, True),
    (["foo/**"], "quux/foo/bar", False, False),
    (["foo/**/**"], "foo", False, False),
    (["foo/**/**"], "foo/", False, False),
    (["foo/**/**"], "foo/bar", False, True),
    (["foo/**/**"], "quux/foo/bar", False, False),
    (["foo/**bar"], "foo/bar", False, True),
    (["foo/**bar"], "foo/qbar", False, True),
    (["foo/**bar"], "foo/glarch/bar", False, False),
    (["foo**/bar"], "foo/glarch/bar", False, True),  # Is this a bug in Git?
    (["foo**/bar"], "fooq/glarch/bar", False, True),  # Is this a bug in Git?
    (["foo**/bar"], "foobar", False, True),  # Is this a bug in Git?
    (["foo**/bar"], "foo/bar", False, True),
    (["foo**/bar"], "fooq/bar", False, True),
    (["foo/**/bar"], "foo/bar", False, True),
    (["foo/**/bar"], "foo/baz/bar", False, True),
    (["foo/**/bar"], "foo/gnusto/cleesh/bar", False, True),
    (["foo/**/**/bar"], "foo/bar", False, True),
    (["foo/**/**/bar"], "foo/baz/bar", False, True),
    (["foo/**/**/bar"], "foo/gnusto/cleesh/bar", False, True),
    (["**/foo"], "foo", False, True),
    (["**/foo"], "bar/foo", False, True),
    (["**/foo"], "quux/bar/foo", False, True),
    (["**/bar*"], "foo/bar", False, True),
    (["**/bar*"], "foo/bar/baz", False, True),
    (["**/bar/*"], "quux/foo/bar/baz", False, True),
    (["**/bar/*"], "quux/foo/bar/baz/", False, True),
    (["**/bar/**"], "quux/foo/bar/baz/", False, True),
    (["**/**"], "quux/foo/bar/baz", False, True),
    (["**/**/foo"], "foo", False, True),
    (["**/**/foo"], "bar/foo", False, True),
    (["**/**/**"], "quux/foo/bar/baz", False, True),
    # Escaping:
    (["f\\oo"], "foo", False, True),
    (["f\\oo"], "f\\oo", False, False),
    (["f\\\\oo"], "f\\oo", False, True),
    (["\\!important"], "!important", False, True),
    (["\\!important"], "important", False, False),
    (["\\#comment"], "#comment", False, True),
    (["\\#comment"], "\\#comment", False, False),
    (["\\*scape"], "*scape", False, True),
    (["\\*scape"], "escape", False, False),
    (["\\*scape"], "scape", False, False),
    (["\\?scape"], "?scape", False, True),
    (["\\?scape"], "escape", False, False),
    (["foo\\*bar"], "foo*bar", False, True),
    (["foo\\*bar"], "foobar", False, False),
    (["foo\\*bar"], "fooquuxbar", False, False),
    (["foo\\*bar"], "foo\\*bar", False, False),
    (["\\x40home"], "@home", False, False),
    (["\\x40home"], "x40home", False, True),
    (["me\\x40home"], "me@home", False, False),
    (["me\\x40home"], "mex40home", False, True),
    (["foo\\", "bar"], "foo", False, False),
    (["foo\\", "bar"], "foo\n", False, False),
    (["foo\\", "bar"], "bar", False, True),
    (["foo\\", "bar"], "foobar", False, False),
    (["foo\\", "bar"], "foo\\bar", False, False),
    (["foo\\", "bar"], "foo\\", False, False),
    (["foo\\\\", "bar"], "foo\\", False, True),
    (["foo\\\\ ", "bar"], "foo\\", False, True),
    (["foo\\\\ ", "bar"], "foo\\ ", False, False),
    (["\\\\"], "\\", False, True),
    (["\\[ab]"], "[ab]", False, True),
    (["\\??\\?b"], "?a?b", False, True),
    (["\\a\\b\\c"], "abc", False, True),
    # Character classes:
    (["[abc]ar"], "bar", False, True),
    (["[abc]ar"], "zar", False, False),
    (["[abc]ar"], "Bar", False, False),
    (["[abc]ar"], "Bar", True, True),
    (["[b-b]ar"], "bar", False, True),
    (["*[ar]?"], "barr", False, True),
    (["*[ar]?"], "bart", False, True),
    (["*[ar]?"], "batr", False, False),
    (["[bar]"], "bar", False, False),
    (["*[!ba]"], "bar", False, True),
    (["*[!ba]"], "bab", False, False),
    (["*[!ba]"], "ba!", False, True),
    (["*[!ba]"], "baz", False, True),
    (["*[ba!]"], "bar", False, False),
    (["*[ba!]"], "bab", False, True),
    (["*[ba!]"], "ba!", False, True),
    (["*[ba!]"], "baz", False, False),
    (["*[!bar]"], "bar", False, False),
    (["b[a-g]r"], "bar", False, True),
    (["b[a-g]r"], "bgr", False, True),
    (["b[a-g]r"], "bfr", False, True),
    (["b[a-g]r"], "bor", False, False),
    (["b[!a-g]r"], "bar", False, False),
    (["b[!a-g]r"], "bgr", False, False),
    (["b[!a-g]r"], "bfr", False, False),
    (["b[!a-g]r"], "bor", False, True),
    (["b[^a-g]r"], "bar", False, False),
    (["b[^a-g]r"], "bgr", False, False),
    (["b[^a-g]r"], "bfr", False, False),
    (["b[^a-g]r"], "bor", False, True),
    (["a[]]b"], "a]b", False, True),
    (["a[]-]b"], "a-b", False, True),
    (["a[]-]b"], "a]b", False, True),
    (["a[]-]b"], "aab", False, False),
    (["a[]a-]b"], "aab", False, True),
    (["]"], "]", False, True),
    (["[!]-]"], "]", False, False),
    (["[!]-]"], "a", False, True),
    (["foo[/]bar"], "foo/bar", False, False),
    (["foo[\\/]bar"], "foo/bar", False, False),
    (["foo[ab/]bar"], "foo/bar", False, False),
    (["foo[^a]bar"], "foo/bar", False, False),
    (["f[^eiu][^eiu][^eiu][^eiu][^eiu]r"], "foo/bar", False, False),
    (["f[^eiu][^eiu][^eiu][^eiu][^eiu]r"], "foo-bar", False, True),
    (["a[c-c]rt"], "acrt", False, True),
    (["[[]ab]"], "[ab]", False, True),
    (["[[:]ab]"], "a", False, False),
    (["[[:]ab]"], "[ab]", False, True),
    (["[[:digit]ab]"], "[ab]", False, True),
    (["[\\[:]ab]"], "[ab]", False, True),
    (["[a-e-n]"], "j", False, False),
    (["[a-e-n]"], "-", False, True),
    (["[a-e-n]"], "b", False, True),
    (["[-]"], "-", False, True),
    (["[\\\\-^]"], "]", False, True),
    (["[\\\\-^]"], "[", False, False),
    (["[\\-_]"], "-", False, True),
    (["[\\]]"], "]", False, True),
    (["[\\]]"], "\\]", False, False),
    (["[\\]]"], "\\", False, False),
    (["[--A]"], "-", False, True),
    (["[--A]"], "5", False, True),
    (["[ --]"], " ", False, True),
    (["[ --]"], "$", False, True),
    (["[ --]"], "-", False, True),
    (["[ --]"], "0", False, False),
    (["[]-a]"], "[", False, False),
    (["[]-a]"], "^", False, True),
    (["[!]-a]"], "[", False, True),
    (["[!]-a]"], "^", False, False),
    (["[\\1-\\3]"], "2", False, True),
    (["[\\1-\\3]"], "3", False, True),
    (["[\\1-\\3]"], "4", False, False),
    (["[a^bc]"], "^", False, True),
    (["[a-]b]"], "-b]", False, True),
    (["[\\]"], "\\", False, False),
    (["[\\,]"], "\\", False, False),
    (["[\\,]"], ",", False, True),
    (["[\\\\]"], "\\", False, True),
    (["[!\\\\]"], "\\", False, False),
    (["[\\\\,]"], ",", False, True),
    (["[\\\\,]"], "\\", False, True),
    (["[[-\\]]"], "\\", False, True),
    (["[[-\\]]"], "[", False, True),
    (["[[-\\]]"], "]", False, True),
    (["[[-\\]]"], "-", False, False),
    (["[A-Z]"], "a", False, False),
    (["[A-Z]"], "a", True, True),
    (["[A-Z]"], "A", False, True),
    (["[a-z]"], "A", False, False),
    (["[a-z]"], "A", True, True),
    (["[a-z]"], "a", False, True),
    (["[B-Za]"], "A", False, False),
    (["[B-Za]"], "A", True, True),
    (["[B-Za]"], "a", False, True),
    (["[B-a]"], "A", False, False),
    (["[B-a]"], "A", True, True),
    (["[B-a]"], "a", False, True),
    (["[Z-y]"], "z", False, False),
    (["[Z-y]"], "z", True, True),
    (["[Z-y]"], "Z", False, True),
    (["[[:]ab"], ":ab", False, True),
    (["[:]ab"], ":ab", False, True),
    # POSIX character classes:
    (["[[:alnum:]]"], "a", False, True),
    (["[[:alnum:]]"], "A", False, True),
    (["[[:alnum:]]"], "q", False, True),
    (["[[:alnum:]]"], "7", False, True),
    (["[[:alnum:]]"], "$", False, False),
    (["[[:alnum:]]"], "_", False, False),
    (["[[:alpha:]]"], "q", False, True),
    (["[[:alpha:]]"], "Q", False, True),
    (["[[:alpha:]]"], "7", False, False),
    (["[[:blank:]]"], " ", False, True),
    (["[[:blank:]]"], "\t", False, True),
    (["[[:blank:]]"], "\n", False, False),
    (["[[:blank:]]"], "\v", False, False),
    (["[[:cntrl:]]"], "\x7F", False, True),
    (["[[:cntrl:]]"], "\n", False, True),
    (["[[:cntrl:]]"], "\t", False, True),
    (["[[:cntrl:]]"], " ", False, False),
    (["[[:cntrl:]]"], "^", False, False),
    (["[[:digit:]]"], "1", False, True),
    (["[[:digit:]]"], "a", False, False),
    (["[[:graph:]]"], "q", False, True),
    (["[[:graph:]]"], "Q", False, True),
    (["[[:graph:]]"], "*", False, True),
    (["[[:graph:]]"], "7", False, True),
    (["[[:graph:]]"], " ", False, False),
    (["[[:lower:]]oo"], "foo", False, True),
    (["[[:lower:]]oo"], "ðoo", False, False),
    (["[[:lower:]]oo"], "Foo", True, True),
    (["[[:lower:]]oo"], "foo", True, True),
    (["[[:lower:]]oo"], "FOO", True, True),
    (["[[:print:]]"], "q", False, True),
    (["[[:print:]]"], "Q", False, True),
    (["[[:print:]]"], "*", False, True),
    (["[[:print:]]"], "7", False, True),
    (["[[:print:]]"], " ", False, True),
    (["[[:print:]]"], "\t", False, False),
    (["[[:print:]]"], "\n", False, False),
    (["[[:punct:]]"], "*", False, True),
    (["[[:punct:]]"], "_", False, True),
    (["[[:punct:]]"], "\\", False, True),
    (["[[:punct:]]"], "~", False, True),
    (["[[:punct:]]"], "0", False, False),
    (["[[:punct:]]"], "p", False, False),
    (["foo[[:punct:]]bar"], "foo/bar", False, False),
    (["foo[^[:punct:]]bar"], "foo/bar", False, False),
    (["[^[:punct:]]"], "x", False, True),
    (["[[:space:]]"], "\t", False, True),
    (["[[:space:]]"], "\n", False, True),
    (["[[:space:]]"], "\r", False, True),
    (["[[:space:]]"], " ", False, True),
    # These two are deliberately not matched by Git's custom isspace() for some
    # reason:
    (["[[:space:]]"], "\v", False, False),
    (["[[:space:]]"], "\f", False, False),
    (["[[:upper:]]"], "A", False, True),
    (["[[:upper:]]"], "a", False, False),
    (["[[:upper:]]"], "a", True, True),
    (["[[:upper:]]"], "Q", False, True),
    (["[[:xdigit:]]"], "5", False, True),
    (["[[:xdigit:]]"], "f", False, True),
    (["[[:xdigit:]]"], "D", False, True),
    (["[[:xdigit:]]"], "g", False, False),
    (["[[:alpha:]][[:digit:]][[:upper:]]"], "a1B", False, True),
    (["[[:digit:][:upper:][:space:]]"], "a", False, False),
    (["[[:digit:][:upper:][:space:]]"], "a", True, True),
    (["[[:digit:][:upper:][:space:]]"], "A", False, True),
    (["[[:digit:][:upper:][:space:]]"], "1", False, True),
    (["[[:digit:][:upper:][:space:]]"], " ", False, True),
    (["[[:digit:][:upper:][:space:]]"], "*", False, False),
    (["[[:digit:][:punct:][:space:]]"], "*", False, True),
    (["[a-c[:digit:]x-z]"], "5", False, True),
    (["[a-c[:digit:]x-z]"], "b", False, True),
    (["[a-c[:digit:]x-z]"], "y", False, True),
    (["[a-c[:digit:]x-z]"], "q", False, False),
    # Whitespace & comments:
    ([" "], " ", False, False),
    (["#comment"], "#comment", False, False),
    ([" #comment"], " #comment", False, True),
    (["trailing "], "trailing", False, True),
    (["trailing "], "trailing ", False, False),
    (["trailing\\ "], "trailing ", False, True),
    (["trailing\\  "], "trailing ", False, True),
    (["trailing\\  "], "trailing  ", False, False),
    (["trailing\\ \\ "], "trailing  ", False, True),
    (["trailing \\ "], "trailing  ", False, True),
    (["foo\v"], "foo\v", False, True),
    (["foo\v"], "foo", False, False),
    # Negation:
    (["!important"], "!important", False, False),
    (["!important"], "important", False, False),
    (["!important"], "foo", False, False),
    (["foo/", "!bar"], "foo/bar", False, True),
    (["foo", "!bar"], "foo/bar", False, True),
    (["!bar", "foo"], "foo/bar", False, True),
    (["file", "!dir"], "dir/file", False, True),
    (["!dir", "file"], "dir/file", False, True),
    (["*.txt", "!foo.txt"], "foo.txt", False, False),
    (["!foo.txt", "*.txt"], "foo.txt", False, True),
    (["*.txt", "!*.txt/"], "foo.txt", False, True),
    (["*.txt", "!*.txt/"], "foo.txt/", False, False),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "foo", False, False),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "quux", False, True),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "quux/gnusto", False, True),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "foo/quux", False, True),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "foo/quux/gnusto", False, True),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "quux/foo/bar", False, True),
    (["/*", "!/foo", "/foo/*", "!/foo/bar"], "foo/bar", False, False),
    # Empty patterns:
    ([""], "foo", False, False),
    (["!"], "foo", False, False),
    (["!/"], "foo/", False, False),
    (["/"], "foo", False, False),
    (["/"], "foo/", False, False),
    # Invalid patterns:
    (["\\"], "\\", False, False),
    (["foo\\/"], "foo\\/", False, False),
    (["foo\\/"], "foo/", False, False),
    (["[z-a]"], "q", False, False),
    (["[!"], "ab", False, False),
    (["[!"], "[!", False, False),
    (["a[]b"], "ab", False, False),
    (["a[]b"], "a[]b", False, False),
    (["ab["], "ab[", False, False),
    (["[-"], "ab", False, False),
    (["[-"], "[", False, False),
    (["[-"], "-", False, False),
    (["[-"], "[-", False, False),
    (["[ab"], "[ab", False, False),
    (["[ab"], "a", False, False),
    (["[^ab"], "[^ab", False, False),
    (["[^ab"], "q", False, False),
    (["[[:XDIGIT:]]"], "5", False, False),
    (["[[:XDIGIT:]]"], "5", True, False),
    (["[[:digit:][:upper:][:spaci:]]"], "1", False, False),
    (["[[::]ab]"], "[ab]", False, False),
    (["[[::]ab]"], "a", False, False),
    (["[[::]ab"], ":ab", False, False),
]


@pytest.mark.parametrize("patterns,path,ignorecase,matched", CASES)
def test_match(patterns: list[str], path: str, ignorecase: bool, matched: bool) -> None:
    if "\\" in path and ON_WINDOWS:
        pytest.skip("Backslashes are path separators on Windows")
    gi = gitmatch.compile(patterns, ignorecase=ignorecase)
    assert bool(gi.match(path)) is matched
    if matched and not ignorecase:
        gii = gitmatch.compile(patterns, ignorecase=True)
        assert gii.match(path)


def test_match_bytes() -> None:
    gi = gitmatch.compile([b"foo", b"!bar"])
    assert gi.match(b"foo")
    assert not gi.match(b"bar")
    assert gi.match(b"foo/bar")


def test_empty_path() -> None:
    gi = gitmatch.compile(["*"])
    with pytest.raises(gitmatch.InvalidPathError) as excinfo:
        gi.match("")
    assert str(excinfo.value) == "Empty path: ''"


def test_nul_in_path() -> None:
    gi = gitmatch.compile(["*"])
    with pytest.raises(gitmatch.InvalidPathError) as excinfo:
        gi.match("foo\0bar")
    assert str(excinfo.value) == "Path contains NUL byte: 'foo\\x00bar'"


def test_absolute_path() -> None:
    path = os.path.abspath(__file__)
    gi = gitmatch.compile(["*"])
    with pytest.raises(gitmatch.InvalidPathError) as excinfo:
        gi.match(path)
    assert str(excinfo.value) == f"Path is not relative: {path!r}"


def test_posix_path() -> None:
    gi = gitmatch.compile([r"foo\\bar"])
    assert gi.match(PurePosixPath("foo\\bar", "quux"))


def test_windows_path() -> None:
    gi = gitmatch.compile(["bar"])
    assert gi.match(PureWindowsPath("foo", "bar"))


def test_explicit_is_dir() -> None:
    gi = gitmatch.compile(["foo/"])
    assert gi.match("foo", is_dir=True)


@pytest.mark.parametrize("path", ["./foo", "foo/.", "foo/..", "foo//bar"])
def test_nonnormalized_path(path: str) -> None:
    gi = gitmatch.compile(["*"])
    with pytest.raises(gitmatch.InvalidPathError) as excinfo:
        gi.match(path)
    assert str(excinfo.value) == f"Path is not normalized: {path!r}"
    assert excinfo.value.path == path


@pytest.mark.parametrize("path", ["..", "../", "../foo"])
def test_pardir_path(path: str) -> None:
    gi = gitmatch.compile(["*"])
    with pytest.raises(gitmatch.InvalidPathError) as excinfo:
        gi.match(path)
    assert str(excinfo.value) == f"Path cannot begin with '..': {path!r}"
    assert excinfo.value.path == path


@pytest.mark.parametrize("pattern", ["*", ".", "*/", "./", ".*", "[[:punct:]]"])
def test_curdir_path(pattern: str) -> None:
    gi = gitmatch.compile([pattern])
    assert not gi.match(".")
    assert not gi.match("./")


def test_retrieve_pattern() -> None:
    gi = gitmatch.compile(["foo ", "!bar"])
    m = gi.match("foo")
    assert m is not None
    assert bool(m)
    assert m.pattern == "foo"
    assert m.path == "foo"
    assert gi.match("quux") is None
    m = gi.match("bar")
    assert m is not None
    assert not bool(m)
    assert m.pattern == "!bar"
    assert m.path == "bar"
    m = gi.match("foo/bar")
    assert m is not None
    assert bool(m)
    assert m.pattern == "foo"
    assert m.path == "foo"


@pytest.mark.parametrize("pattern", ["", " ", "#comment", "!", "!/", "/", "! ", "/ "])
def test_empty_pattern(pattern: str) -> None:
    assert gitmatch.pattern2regex(pattern) is None


@pytest.mark.parametrize(
    "pattern",
    [
        "\\",
        "foo\\/",
        "[z-a]",
        "[!",
        "a[]b",
        "ab[",
        "[-",
        "[ab",
        "[^ab",
        "[[:XDIGIT:]]",
        "[[:glarch:]]",
        "[[::]ab]",
        "[[::]ab",
        "foo\0bar",
    ],
)
def test_invalid_pattern(pattern: str) -> None:
    with pytest.raises(gitmatch.InvalidPatternError) as excinfo:
        gitmatch.pattern2regex(pattern)
    assert str(excinfo.value) == f"Invalid gitignore pattern: {pattern!r}"
    assert excinfo.value.pattern == pattern


@pytest.mark.parametrize("pattern", ["foo\n", "foo\r", "foo\r\n"])
def test_strip_newlines(pattern: str) -> None:
    gi = gitmatch.compile([pattern])
    m = gi.match("foo")
    assert m is not None
    assert m.pattern == "foo"


@pytest.fixture(scope="module")
def repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    p = tmp_path_factory.mktemp("repo")
    subprocess.run(["git", "init"], cwd=p, check=True)
    return p


@pytest.mark.skipif(shutil.which("git") is None, reason="Git not installed")
@pytest.mark.parametrize("patterns,path,ignorecase,matched", CASES)
def test_check_against_git(
    repo: Path, patterns: list[str], path: str, ignorecase: bool, matched: bool
) -> None:
    # <https://stackoverflow.com/a/31976060/744178>
    if ON_WINDOWS and re.search(r'[<>:"\x5C|?*\0-\x1F]|[ .](/|\Z)', path):
        pytest.skip("Path is invalid on Windows")
    if ON_WINDOWS and ON_PYPY and not path.isascii():
        pytest.skip("Non-ASCII filenames are a problem for PyPy on Windows")
    (repo / ".gitignore").write_text(join_terminated(patterns, "\n"), encoding="utf-8")
    p = Path(path)
    (repo / p).parent.mkdir(parents=True, exist_ok=True)
    if path.endswith("/"):
        (repo / p).mkdir()
        # A tree containing only directories will only show up in `git status`
        # if it's ignored, so in order to ensure a "status" entry for `path`,
        # we add a file.
        (repo / p / "XYZZY").touch()
    else:
        (repo / p).touch()
    # Don't use git-check-ignore, as it's not 100% accurate for directories
    r = subprocess.run(
        [
            "git",
            "-c",
            f"core.ignorecase={ignorecase}",
            "status",
            "--ignored=matching",
            "--porcelain",
            "-z",
        ],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        # Don't use `text=True`, as that translates newlines in filenames
    )
    ((status, statpath),) = [
        (line[:2], line[3:])
        for line in split_terminated(os.fsdecode(r.stdout), "\0")
        if line[3:] != ".gitignore"
    ]
    pathway = gitmatch.pathway(path)
    for i in range(len(pathway) - 1):
        pathway[i] += "/"
    try:
        # Make sure we're ignoring `path` or a parent thereof and not
        # `{path}/XYZZY`
        assert (status == "!!" and statpath in pathway) is matched
    finally:
        base = repo / p.parts[0]
        if base.is_file():
            base.unlink()
        else:
            shutil.rmtree(base)
