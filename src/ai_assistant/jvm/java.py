# coding: utf-8

"""Wrapper for base Java classes imported through the JVM."""

from ..jvm import startJVM
from ..logging import logger

__all__ = []

try:
    # Make sure JVM is running before performing imports
    startJVM()

    import java.util.ArrayList as ArrayList
    import java.util.Collection as Collection
    import java.util.Collections as Collections
    import java.util.HashSet as HashSet
    import java.util.List as List
    import java.util.Set as Set
    import java.io.ByteArrayInputStream as ByteArrayInputStream

    __all__ += [
        "ArrayList",
        "Collection",
        "Collections",
        "HashSet",
        "List",
        "Set",
        "ByteArrayInputStream",
    ]
except TypeError as e:
    logger.error("Cannot start JVM", e)
