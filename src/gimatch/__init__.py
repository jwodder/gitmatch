"""
Gitignore-style path matching

Visit <https://github.com/jwodder/gimatch> for more information.
"""

from __future__ import annotations
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import os
from pathlib import PureWindowsPath
import posixpath
import re
from typing import Any, AnyStr, Generic, Optional

__version__ = "0.1.0.dev1"
__author__ = "John Thorvald Wodder II"
__author_email__ = "gimatch@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/gimatch"


@dataclass
class Gitignore(Generic[AnyStr]):
    patterns: list[Pattern[AnyStr]]

    def match(self, path: AnyStr | os.PathLike[AnyStr], is_dir: bool = False) -> bool:
        orig = path
        path = os.fspath(path)
        if isinstance(path, str):
            NUL = "\0"
            SLASH = "/"
            SEP = os.sep
            WINSEP = "\\"
            CURDIR = "."
            PARDIR = ".."
        else:
            NUL = b"\0"
            SLASH = b"/"
            SEP = os.sep.encode("us-ascii")
            WINSEP = b"\\"
            CURDIR = b"."
            PARDIR = b".."
        if not path:
            raise InvalidPathError(f"Empty path: {orig!r}")
        if NUL in path:
            raise InvalidPathError(f"Path contains NUL byte: {orig!r}")
        if os.path.isabs(path):
            raise InvalidPathError(f"Path is not relative: {orig!r}")
        if SEP != SLASH:
            path = path.replace(SEP, SLASH)
        elif isinstance(orig, PureWindowsPath):
            path = path.replace(WINSEP, SLASH)
        if path.endswith(SLASH):
            is_dir = True
            path = path[:-1]
        if posixpath.normpath(path) != path:
            raise InvalidPathError(f"Path is not normalized: {orig!r}")
        if path.split(SLASH)[0] == PARDIR:
            raise InvalidPathError(f"Path cannot begin with '..': {orig!r}")
        if path == CURDIR:
            return False
        for p in pathway(path):
            for pat in reversed(self.patterns):
                if pat.match(p, is_dir=(is_dir if p == path else True)):
                    if not pat.negative:
                        return True
                    elif p == path:
                        return False
                    else:
                        break
        return False


@dataclass
class Pattern(Generic[AnyStr]):
    regex: re.Pattern[AnyStr]
    negative: bool
    dir_only: bool

    def match(self, path: AnyStr, is_dir: bool = False) -> bool:
        if self.dir_only and not is_dir:
            return False
        return bool(self.regex.fullmatch(path))


@dataclass
class Regex(Generic[AnyStr]):
    regex: AnyStr
    negative: bool
    dir_only: bool

    def compile(self) -> Pattern[AnyStr]:
        return Pattern(
            regex=re.compile(self.regex), negative=self.negative, dir_only=self.dir_only
        )


def compile(patterns: Iterable[AnyStr], ignorecase: bool = False) -> Gitignore[AnyStr]:
    compiled_patterns: list[Pattern[AnyStr]] = []
    for pat in patterns:
        try:
            regex = pattern2regex(pat, ignorecase=ignorecase)
        except InvalidPatternError:
            continue
        if regex is None:
            continue
        compiled_patterns.append(regex.compile())
    return Gitignore(compiled_patterns)


@dataclass
class ParserStrs(Generic[AnyStr]):
    posix_classes: dict[AnyStr, AnyStr]
    parser: re.Pattern[AnyStr]
    range_parser: re.Pattern[AnyStr]
    crlf: AnyStr
    octothorpe: AnyStr
    bang: AnyStr
    slash: AnyStr
    start: AnyStr
    istart: AnyStr
    end: AnyStr
    leading_globstar_slash: re.Pattern[AnyStr]
    is_anchored: re.Pattern[AnyStr]
    unanchored_start: AnyStr
    slash_globstar: AnyStr
    slash_globstar_slash: AnyStr
    globstar_slash: AnyStr
    qm: AnyStr
    star: AnyStr
    openrange: AnyStr
    caret: AnyStr
    close_bracket: AnyStr
    close_bracket_in_range: re.Pattern[AnyStr]
    hyphen: AnyStr

    def encode(self: ParserStrs[str]) -> ParserStrs[bytes]:
        return ParserStrs(
            **{name: self.encode_field(value) for name, value in asdict(self).items()}
        )

    @staticmethod
    def encode_field(value: Any) -> Any:
        if isinstance(value, str):
            return value.encode("us-ascii")
        elif isinstance(value, re.Pattern):
            return re.compile(
                value.pattern.encode("us-ascii"), flags=value.flags & ~re.U
            )
        elif isinstance(value, dict):
            return {
                k.encode("us-ascii"): v.encode("us-ascii") for k, v in value.items()
            }
        else:
            raise TypeError(value)


PARSER_STRS = ParserStrs(
    posix_classes={
        "alpha": r"A-Za-z",
        "alnum": r"A-Za-z0-9",
        "blank": r" \t",
        "cntrl": r"\0-\x1F\x7F",
        "digit": r"0-9",
        "graph": r"!-\~",
        "lower": r"a-z",
        "print": r" -\~",
        "punct": r"!-/:-@[-`{-\~",
        "space": r"\t\n\r ",
        "upper": r"A-Z",
        "xdigit": r"0-9A-Fa-f",
    },
    parser=re.compile(
        r"""
        (?P<slash_globstar>/\*\*\Z)
        |(?P<slash_globstar_slash>/\*\*(/\*\*)*/)
        |(?P<globstar_slash>\*\*/(\*\*/)*)
        |(?P<qm>\?)
        |(?P<star>\*\*?)
        |(?P<openrange>\[)
        |(?P<char>\x5C[^\0]|[^\0\x5C])
    """,
        flags=re.X,
    ),
    range_parser=re.compile(
        r"""
        (?P<left>\x5C[^\0]|[^\0\x5C])-(?P<right>\x5C[^\0]|[^\0\x5C\x5D])
        |\[:(?P<posix_class>[^\]]*):\]
        |(?P<char>\x5C[^\0]|[^\0\x5C\x5D])
        |(?P<end>\])
    """,
        flags=re.X,
    ),
    crlf="\r\n",
    octothorpe="#",
    bang="!",
    slash="/",
    start=r"(?a:",
    istart=r"(?ai:",
    end=r")",
    leading_globstar_slash=re.compile(r"\*\*/(?:\*\*/)*"),
    is_anchored=re.compile(r"^/|/."),
    unanchored_start=r"(?:[^/\0]+/)*",
    slash_globstar=r"(?:(?:/[^/\0]+)+/?|/)",
    slash_globstar_slash=r"/(?:[^/\0]+/)*",
    globstar_slash=r"(?:[^/\0]*/)?(?:[^/\0]+/)*",
    qm=r"[^/\0]",
    star=r"[^/\0]*",
    openrange=r"(?![/\0])[",
    caret="^",
    close_bracket="]",
    close_bracket_in_range=re.compile(r"\](?!-[^\]])"),
    hyphen="-",
)

PARSER_BYTES = PARSER_STRS.encode()


def pattern2regex(pattern: AnyStr, ignorecase: bool = False) -> Optional[Regex[AnyStr]]:
    strs: ParserStrs
    if isinstance(pattern, str):
        strs = PARSER_STRS
    else:
        strs = PARSER_BYTES
    orig = pattern
    pattern = trim_trailing_spaces(pattern.rstrip(strs.crlf))
    if pattern.startswith(strs.octothorpe):
        return None
    if pattern.startswith(strs.bang):
        negative = True
        pattern = pattern[1:]
        if not pattern:
            return None
    else:
        negative = False
    if pattern.endswith(strs.slash):
        dir_only = True
        pattern = pattern[:-1]
    else:
        dir_only = False
    if not pattern:
        return None
    pos = 0
    regex = strs.istart if ignorecase else strs.start
    m = strs.leading_globstar_slash.match(pattern)
    if m or not strs.is_anchored.search(pattern):
        regex += strs.unanchored_start
        if m:
            pos += m.end()
    if not m and pattern.startswith(strs.slash):
        pos += 1
    while pos < len(pattern):
        m = strs.parser.match(pattern, pos)
        if not m:
            raise InvalidPatternError(f"Invalid gitignore pattern: {orig!r}")
        pos += m.end() - m.start()
        if m["slash_globstar"] is not None:
            regex += strs.slash_globstar
        elif m["slash_globstar_slash"] is not None:
            regex += strs.slash_globstar_slash
        elif m["globstar_slash"] is not None:
            regex += strs.globstar_slash
        elif m["qm"] is not None:
            regex += strs.qm
        elif m["star"] is not None:
            regex += strs.star
        elif m["openrange"] is not None:
            regex += strs.openrange
            if pattern[pos : pos + 1] in (strs.caret, strs.bang):
                regex += strs.caret
                pos += 1
            if strs.close_bracket_in_range.match(pattern, pos=pos):
                regex += strs.close_bracket
                pos += 1
            while True:
                m = strs.range_parser.match(pattern, pos)
                if not m:
                    raise InvalidPatternError(f"Invalid gitignore pattern: {orig!r}")
                pos += m.end() - m.start()
                if m["left"] is not None:
                    regex += (
                        re.escape(m["left"][-1:])
                        + strs.hyphen
                        + re.escape(m["right"][-1:])
                    )
                elif m["posix_class"] is not None:
                    try:
                        regex += strs.posix_classes[m["posix_class"]]
                    except KeyError:
                        raise InvalidPatternError(
                            f"Invalid gitignore pattern: {orig!r}"
                        )
                elif m["char"] is not None:
                    regex += re.escape(m["char"][-1:])
                elif m["end"] is not None:
                    regex += strs.close_bracket
                    break
                else:
                    raise AssertionError(
                        "Unhandled pattern structure"
                    )  # pragma: no cover
        elif m["char"] is not None:
            regex += re.escape(m["char"][-1:])
        else:
            raise AssertionError("Unhandled pattern structure")  # pragma: no cover
    regex += strs.end
    return Regex(regex, negative, dir_only=dir_only)


class InvalidPathError(ValueError):
    pass


class InvalidPatternError(ValueError):
    pass


def pathway(path: AnyStr) -> list[AnyStr]:
    pway: list[AnyStr] = []
    while path:
        pway.append(path)
        path = posixpath.dirname(path)
    pway.reverse()
    return pway


TRIM_RGX = r"(?<!\\)(?P<keep>(?:\\\\)*(\\[ \t])?)[ \t]*\Z"
TRIM_STR = re.compile(TRIM_RGX)
TRIM_BYTES = re.compile(TRIM_RGX.encode("us-ascii"))


def trim_trailing_spaces(s: AnyStr) -> AnyStr:
    if isinstance(s, str):
        rgx = TRIM_STR
        keep = r"\g<keep>"
    else:
        rgx = TRIM_BYTES
        keep = rb"\g<keep>"
    return rgx.sub(keep, s)
