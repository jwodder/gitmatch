.. currentmodule:: gitmatch

API
===

Functions
---------
.. autofunction:: compile
.. autofunction:: pattern2regex

Classes
-------

.. note::

    Although the Sphinx docs don't show it, all of the ``gitmatch`` classes are
    generic in `typing.AnyStr`; i.e., they should be written in type
    annotations as ``Gitignore[AnyStr]``, ``Gitignore[str]``, or
    ``Gitignore[bytes]``, as appropriate.

.. autoclass:: Gitignore()
.. autoclass:: Pattern()
.. autoclass:: Regex()
.. autoclass:: Match()

Exceptions
----------
.. autoexception:: InvalidPathError()
    :show-inheritance:
.. autoexception:: InvalidPatternError()
    :show-inheritance:
