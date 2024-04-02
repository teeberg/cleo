from __future__ import annotations

import functools
import sys


if sys.version_info < (3, 11):
    import typing

    _cleanups = []
    _caches = {}

    def _tp_cache(func=None, /, *, typed=False):
        """Internal wrapper caching __getitem__ of generic types.

        For non-hashable arguments, the original function is used as a fallback.
        """

        def decorator(func):
            # The callback 'inner' references the newly created lru_cache
            # indirectly by performing a lookup in the global '_caches' dictionary.
            # This breaks a reference that can be problematic when combined with
            # C API extensions that leak references to types. See GH-98253.

            cache = functools.lru_cache(typed=typed)(func)
            _caches[func] = cache
            _cleanups.append(cache.cache_clear)
            del cache

            @functools.wraps(func)
            def inner(*args, **kwds):
                try:
                    return _caches[func](*args, **kwds)
                except TypeError:
                    pass  # All real errors (not unhashable args) are raised below.
                return func(*args, **kwds)

            return inner

        if func is not None:
            return decorator(func)

        return decorator

    class Self(_root=True):
        """Used to spell the type of "self" in classes.

        Example::

            from typing import Self

            class Foo:
                def return_self(self) -> Self:
                    ...
                    return self

        This is especially useful for:
            - classmethods that are used as alternative constructors
            - annotating an `__enter__` method which returns self
        """

        __slots__ = ("_name", "__doc__", "_getitem", "__weakref__")

        def __init__(self, getitem):
            self._getitem = getitem
            self._name = "Self"

        def __getattr__(self, item):
            if item in {"__name__", "__qualname__"}:
                return self._name

            raise AttributeError(item)

        def __mro_entries__(self, bases):
            raise TypeError(f"Cannot subclass {self!r}")

        def __repr__(self):
            return f"typing_extensions.{self._name}"

        def __reduce__(self):
            return self._name

        def __call__(self, *args, **kwds):
            raise TypeError(f"Cannot instantiate {self!r}")

        def __or__(self, other):
            return typing.Union[self, other]

        def __ror__(self, other):
            return typing.Union[other, self]

        def __instancecheck__(self, obj):
            raise TypeError(f"{self} cannot be used with isinstance()")

        def __subclasscheck__(self, cls):
            raise TypeError(f"{self} cannot be used with issubclass()")

        @_tp_cache
        def __getitem__(self, parameters):
            return self._getitem(self, parameters)

        def __init_subclass__(cls, /, *args, **kwds):
            if "_root" not in kwds:
                raise TypeError("Cannot subclass special typing classes")

else:
    from typing import Self


__all__ = [
    "Self",
]
