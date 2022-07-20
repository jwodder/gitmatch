.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.

.. image:: https://github.com/jwodder/gitmatch/workflows/Test/badge.svg?branch=master
    :target: https://github.com/jwodder/gitmatch/actions?workflow=Test
    :alt: CI Status

.. image:: https://codecov.io/gh/jwodder/gitmatch/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/jwodder/gitmatch

.. image:: https://img.shields.io/pypi/pyversions/gitmatch.svg
    :target: https://pypi.org/project/gitmatch/

.. image:: https://img.shields.io/github/license/jwodder/gitmatch.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/gitmatch>`_
| `PyPI <https://pypi.org/project/gitmatch/>`_
| `Documentation <https://gitmatch.readthedocs.io>`_
| `Issues <https://github.com/jwodder/gitmatch/issues>`_

``gitmatch`` provides ``gitignore``-style pattern matching of file paths.
Simply pass in a sequence of ``gitignore`` patterns and you'll get back an
object for testing whether a given relative path matches the patterns.

Installation
============
``gitmatch`` requires Python 3.7 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install gitmatch


Examples
========

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
