.. image:: http://www.repostatus.org/badges/latest/wip.svg
    :target: http://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

.. image:: https://github.com/jwodder/gitmatch/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/gitmatch/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/gitmatch/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/gitmatch

.. image:: https://img.shields.io/github/license/jwodder/gitmatch.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/gitmatch>`_
| `Issues <https://github.com/jwodder/gitmatch/issues>`_

``gitmatch`` provides ``gitignore``-style pattern matching of file paths.
Simply pass in a sequence of ``gitignore`` patterns and you'll get back an
object for testing whether a given relative path matches the patterns.

Installation
============
``gitmatch`` requires Python 3.7 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/gitmatch


Example
=======

Basic usage::

    >>> import gitmatch
    >>> gi = gitmatch.compile(["foo", "!bar", "*.dir/"])
    >>> bool(gi.match("foo"))
    True
    >>> bool(gi.match("bar"))
    False
    >>> bool(gi.match("quux"))
    False
    >>> bool(gi.match("foo/quux"))
    True
    >>> bool(gi.match("foo/bar"))
    True
    >>> bool(gi.match("bar/foo"))
    True
    >>> bool(gi.match("bar/quux"))
    False
    >>> bool(gi.match("foo.dir"))
    False
    >>> bool(gi.match("foo.dir/"))
    True

See what pattern was matched::

    >>> m1 = gi.match("foo/bar")
    >>> m1 is None
    False
    >>> bool(m1)
    True
    >>> m1.pattern
    'foo'
    >>> m1.path
    'foo'
    >>> m2 = gi.match("bar")
    >>> m2 is None
    False
    >>> bool(m2)
    False
    >>> m2.pattern
    '!bar'
    >>> m2.pattern_obj.negative
    True
    >>> m3 = gi.match("quux")
    >>> m3 is None
    True


Patterns
========

The pattern language used by ``gitmatch`` is intended to match that of Git's
`gitignore(5)`__ as of v2.36.1, including the undocumented features (mainly
involving character classes) present in Git's code.

__ https://git-scm.com/docs/gitignore

Specifically:

- A pattern that starts with a ``#`` or is empty (after stripping trailing
  whitespace, a trailing ``/``, and an initial ``!``) is discarded

- Trailing space and tab characters in a pattern are stripped unless they are
  escaped with a backslash (which must itself not be escaped by another
  backslash)

- The forward slash (``/``) is used as the directory separator, even on Windows

- An initial ``!`` negates the pattern; if a path matches a negated pattern,
  then any matches against previous patterns in the pattern list will be
  discarded.

- ``?`` matches any character other than ``/``

- ``*`` matches zero or more of any character other than ``/``

- A leading or medial ``/`` anchors the pattern to the start of the path; if no
  such ``/`` is present, the pattern will match any path in which it is
  preceded by zero or more ``/``-separated path components, each one composed
  of one or more non-``/`` characters

- A trailing ``/`` causes the pattern to only match directories

- An initial ``**/`` matches zero or more ``/``-separated path components

- A trailing ``/**`` matches one or more ``/``-separated path components

- ``/**/`` matches zero or more intervening ``/``-separated path components;
  e.g., ``foo/**/bar`` matches ``foo/bar``, ``foo/gnusto/bar``,
  ``foo/gnusto/cleesh/bar``, etc, but not ``fooxbar``.  Any following ``**/``
  (e.g., as in ``foo/**/**/**/bar``) are redundant.

- ``**`` in any other context is the same as ``*``

- ``[`` starts a character class, which must be terminated by ``]``.  A
  character class will match any one character from the set of characters
  specified within.  Characters can be specified as either themselves (e.g.,
  ``[abc]`` matches ``a``, ``b``, or ``c``) and/or as ranges (e.g., ``[a-f]``
  matches any letter from ``a`` through ``f``).

  - A character class can be inverted (making it match any character except
    those specified) by inserting ``!`` or ``^`` after the opening ``[``

  - A ``]`` can be included in a character set by either escaping it or by
    placing it immediately after the opening ``[`` and optional ``!``/``^``.

    - In order for a ``]`` to be used on the right side of a range, it must be
      escaped with a backslash; otherwise, it indicates the end of the
      character class, and the preceding hyphen and character before it will be
      treated literally rather than as a range.

  - Within a character class, an occurrence of ``[:PROPERTY:]`` will cause the
    class to include the ASCII characters with the given property; supported
    properties are:

    - ``alnum`` — letters and numbers
    - ``alpha`` — letters
    - ``blank`` — space and tab character
    - ``cntrl`` — any character with an ASCII value less than 0x20, plus the
      DEL (0x7F) character
    - ``digit`` — numbers
    - ``graph`` — letters, numbers, and punctuation
    - ``lower`` — lowercase letters
    - ``print`` — letters, numbers, punctuation, and the space character
    - ``punct`` — punctuation
    - ``space`` — space character, tab, line feed, and carriage return
    - ``upper`` — uppercase letters
    - ``xdigit`` — hexadecimal digits

    An unknown ``PROPERTY`` produces an invalid pattern that will not match
    anything.

  - A character class will never match a ``/``

- Any character (special or not) in a pattern may be deprived of any special
  meaning by preceding it with a backslash.  A backslash that is not followed
  by a character (after stripping a final ``/``) produces an invalid pattern
  that will not match anything.

- Patterns cannot contain the NUL character

- If a directory path matches a pattern list, then all files & directories
  within that directory recursively will match as well, regardless of any
  negative patterns that may apply to them

- A path containing a NUL character will never match any pattern

- A pattern will never match the current directory


Strings vs. Bytes
=================

While it's usual in Python to work with ``str`` values of Unicode characters,
Git instead operates on bytes.  As a result, if a path or pattern contains
non-ASCII characters, you may get different results using ``str``\s with
``gitmatch`` than you would with Git.  For example, in Git, a file named
"``tést``" will not be matched by the gitignore pattern ``t?st``, because the
``é`` is encoded using more than one byte (assuming UTF-8), but if you pass
these strings to ``gitmatch``, the path will match (assuming the ``é`` is in
composed form, which is a whole other can of worms).  If you want Git's
behavior exactly, pass ``bytes`` to ``gitmatch`` instead of ``str`` (ideally
encoded using ``os.fsencode()``).

Note that the patterns passed to a single call to ``compile()`` must be either
all ``str`` or all ``bytes``, and a ``Gitignore`` instance constructed from
``str`` patterns can only match against ``str`` paths, while one constructed
from ``bytes`` patterns can only match against ``bytes`` paths.  (For the
record, the ``pathlib`` classes count as ``str`` paths.)
