# coding: utf-8

"""JVM integration module and utilities."""

import os
import sys
import inspect

import jpype
import jpype.imports


JVM_RUNTIME = os.path.join(
        os.path.dirname(inspect.getabsfile(sys.modules[__name__])),
        "ai-assistant.jar",
)


def startJVM(*args, classpath=[JVM_RUNTIME], **kwargs) -> None:
    if not jpype.isJVMStarted():
        jpype.startJVM(*args, classpath=classpath, **kwargs)
