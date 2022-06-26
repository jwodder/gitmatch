.. image:: http://www.repostatus.org/badges/latest/wip.svg
    :target: http://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

.. image:: https://github.com/jwodder/gimatch/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/gimatch/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/gimatch/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/gimatch

.. image:: https://img.shields.io/github/license/jwodder/gimatch.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/gimatch>`_
| `Issues <https://github.com/jwodder/gimatch/issues>`_

``gimatch`` provides ``gitignore``-style pattern matching of file paths.
Simply pass in a sequence of ``gitignore`` patterns and you'll get back an
object for testing whether a given relative path matches the patterns.

Installation
============
``gimatch`` requires Python 3.7 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/gitmatch


Example
=======

>>> import gimatch
>>> gi = gimatch.compile(["foo", "!bar"])
>>> gi.match("foo")
True
>>> gi.match("bar")
False
>>> gi.match("quux")
False
>>> gi.match("foo/quux")
True
>>> gi.match("foo/bar")
True
>>> gi.match("bar/foo")
True
>>> gi.match("bar/quux")
False


Patterns
========

The pattern language used by ``gimatch`` is intended to match that of Git's
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